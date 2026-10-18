"""Local Vietnamese recognition of detected lines, without runtime downloads."""
from pathlib import Path
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher


class _OfflineVietOcrPredictor:
    """VietOCR predictor that never imports its optional download helpers."""

    def __init__(self, config):
        import torch
        from vietocr.tool.translate import build_model

        self.config = config
        self.model, self.vocab = build_model(config)
        self.model.load_state_dict(torch.load(config["weights"], map_location=torch.device(config["device"])))
        self.device = config["device"]

    def predict(self, image, return_prob=False):
        from vietocr.tool.translate import process_input, translate, translate_beam_search

        dataset = self.config["dataset"]
        image = process_input(
            image,
            dataset["image_height"],
            dataset["image_min_width"],
            dataset["image_max_width"],
        ).to(self.device)
        if self.config["predictor"]["beamsearch"]:
            sentence = translate_beam_search(image, self.model)
            probability = None
        else:
            sentence, probability = translate(image, self.model)
            sentence = sentence[0].tolist()
            probability = probability[0]
        text = self.vocab.decode(sentence)
        return (text, probability) if return_prob else text

    def predict_batch(self, images, return_prob=False):
        import torch
        from vietocr.tool.translate import process_input, translate

        dataset = self.config["dataset"]
        buckets = defaultdict(list)
        bucket_indices = defaultdict(list)
        for index, image in enumerate(images):
            tensor = process_input(
                image,
                dataset["image_height"],
                dataset["image_min_width"],
                dataset["image_max_width"],
            )
            buckets[tensor.shape[-1]].append(tensor)
            bucket_indices[tensor.shape[-1]].append(index)

        texts = [""] * len(images)
        probabilities = [0.0] * len(images)
        for width, batch_images in buckets.items():
            sentences, scores = translate(torch.cat(batch_images, 0).to(self.device), self.model)
            decoded = self.vocab.batch_decode(sentences.tolist())
            for index, text, score in zip(bucket_indices[width], decoded, scores.tolist()):
                texts[index] = text
                probabilities[index] = score
        return (texts, probabilities) if return_prob else texts


class VietnameseLineRefiner:
    def __init__(self, model_dir: Path):
        self.weights = model_dir / "vietocr_vgg_transformer.pth"
        self._predictor = None

    @staticmethod
    def _fold(text):
        text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
        return "".join(c for c in text if not unicodedata.combining(c) and c.isalnum())

    @classmethod
    def accept(cls, original, candidate, confidence):
        # Never let a language recognizer change identifiers/contact details.
        original = re.sub(r"^S[0o]\s+", "Số ", original, flags=re.IGNORECASE)
        return (confidence >= 0.8
                and re.findall(r"\d+", original) == re.findall(r"\d+", candidate)
                and SequenceMatcher(None, cls._fold(original), cls._fold(candidate)).ratio() >= 0.92)

    def _load(self):
        if self._predictor is None:
            import torch
            torch.set_num_threads(min(torch.get_num_threads(), 2))
            config = {
                "vocab": 'aAàÀảẢãÃáÁạẠăĂằẰẳẲẵẴắẮặẶâÂầẦẩẨẫẪấẤậẬbBcCdDđĐeEèÈẻẺẽẼéÉẹẸêÊềỀểỂễỄếẾệỆfFgGhHiIìÌỉỈĩĨíÍịỊjJkKlLmMnNoOòÒỏỎõÕóÓọỌôÔồỒổỔỗỖốỐộỘơƠờỜởỞỡỠớỚợỢpPqQrRsStTuUùÙủỦũŨúÚụỤưƯừỪửỬữỮứỨựỰvVwWxXyYỳỲỷỶỹỸýÝỵỴzZ0123456789!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ ',
                "device": "cpu", "weights": str(self.weights), "backbone": "vgg19_bn",
                "cnn": {"pretrained": False, "ss": [[2,2],[2,2],[2,1],[2,1],[1,1]],
                        "ks": [[2,2],[2,2],[2,1],[2,1],[1,1]], "hidden": 256},
                "seq_modeling": "transformer",
                "transformer": {"d_model": 256, "nhead": 8, "num_encoder_layers": 6,
                    "num_decoder_layers": 6, "dim_feedforward": 2048, "max_seq_length": 1024,
                    "pos_dropout": 0.1, "trans_dropout": 0.1},
                "dataset": {"image_height": 32, "image_min_width": 32, "image_max_width": 512},
                "predictor": {"beamsearch": False},
            }
            self._predictor = _OfflineVietOcrPredictor(config)
        return self._predictor

    @classmethod
    def restore_accents(cls, original, candidate):
        """Borrow only matching words; never introduce a guessed extra word."""
        words = re.findall(r"\w+|\W+", original)
        alternatives = re.findall(r"\w+", candidate)
        position = 0
        for index, word in enumerate(words):
            if not word.isalpha():
                continue
            for offset in range(position, min(position + 4, len(alternatives))):
                alternative = alternatives[offset]
                if cls._fold(word) == cls._fold(alternative):
                    if any(ord(c) > 127 for c in alternative):
                        words[index] = alternative
                    position = offset + 1
                    break
        return "".join(words)

    def refine(self, image, lines):
        if not self.weights.is_file():
            return lines
        from PIL import Image
        crops, indices = [], []
        in_address = False
        for index, (box, text, score) in enumerate(lines):
            folded = self._fold(text)
            if folded.startswith("2diachi"):
                in_address = True
            elif folded.startswith(("dienthoai", "sofax", "3thongtin")):
                in_address = False
            if not in_address and not any(word in folded for word in ("congty", "thuongmai", "dichvu", "diadiemkinhdoanh")):
                continue
            if len(text) < 8 or "@" in text or sum(c.isalpha() for c in text) < 6:
                continue
            xs, ys = zip(*box)
            crop = image[max(0, int(min(ys))-2):int(max(ys))+3,
                         max(0, int(min(xs))-2):int(max(xs))+3]
            if crop.size:
                crops.append(Image.fromarray(crop[:, :, ::-1]))
                indices.append(index)
        if not crops:
            return lines
        predictor = self._load()
        result = list(lines)
        for start in range(0, len(crops), 8):
            texts, scores = [], []
            for crop in crops[start:start+8]:
                if crop.width > crop.height * 20:
                    # Split very long lines at an actual whitespace column so
                    # Vietnamese marks survive resizing to the model width.
                    import numpy as np
                    gray = np.asarray(crop.convert("L"))
                    low, high = int(crop.width * .35), int(crop.width * .65)
                    ink = (gray < 180).sum(axis=0)
                    split = low + int(ink[low:high].argmin())
                    parts = [crop.crop((0, 0, split, crop.height)),
                             crop.crop((split, 0, crop.width, crop.height))]
                    words, probabilities = predictor.predict_batch(parts, return_prob=True)
                    texts.append(" ".join(words))
                    scores.append(min(probabilities))
                else:
                    text, score = predictor.predict(crop, return_prob=True)
                    texts.append(text)
                    scores.append(score)
            for index, text, score in zip(indices[start:start+8], texts, scores):
                box, original, original_score = lines[index]
                if self.accept(original, text, score):
                    result[index] = (box, self.restore_accents(original, text), float(score))
        return result
