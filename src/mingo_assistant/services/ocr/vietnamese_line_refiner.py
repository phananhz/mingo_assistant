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
        self.address_candidates = {}

    @staticmethod
    def _fold(text):
        text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
        return "".join(c for c in text if not unicodedata.combining(c) and c.isalnum())

    @classmethod
    def accept(cls, original, candidate, confidence):
        # Never let a language recognizer change identifiers/contact details.
        original = re.sub(r"^S[0o]\s+", "Số ", original, flags=re.IGNORECASE)
        original_words = re.findall(r"[^\W\d_]+", original, flags=re.UNICODE)
        candidate_words = re.findall(r"[^\W\d_]+", candidate, flags=re.UNICODE)
        word_count_is_safe = abs(len(original_words) - len(candidate_words)) <= 1
        return (confidence >= 0.76
                and re.findall(r"\d+", original) == re.findall(r"\d+", candidate)
                and word_count_is_safe
                and SequenceMatcher(None, cls._fold(original), cls._fold(candidate)).ratio() >= 0.84)

    @classmethod
    def looks_like_address_label(cls, text):
        folded = re.sub(r"^2", "", cls._fold(text), count=1)
        return (
            any(marker in folded for marker in ("diachi", "djachi", "dachi", "dijachi", "dach"))
            or SequenceMatcher(None, folded[:8], "diachi").ratio() >= 0.62
        )

    @classmethod
    def looks_like_certificate_heading(cls, text):
        folded = cls._fold(text)
        return "giaychungnh" in folded and (
            "doanhnghiep" in folded or "diadiemkinhdoanh" in folded or "diadimkinhdoanh" in folded
        )

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
                # Keep long address/name rows wide enough that Vietnamese
                # vowels and tone marks are not squeezed out before decoding.
                "dataset": {"image_height": 32, "image_min_width": 32, "image_max_width": 1024},
                "predictor": {"beamsearch": False},
            }
            self._predictor = _OfflineVietOcrPredictor(config)
        return self._predictor

    @classmethod
    def restore_accents(cls, original, candidate, *, allow_letter_repairs=True, advance_unmatched=False):
        """Repair matched words without adding words or changing any digits.

        Exact folded matches restore accents. A close match may also restore
        one or two letters dropped by the general recognizer, for example
        ``Nguyn`` -> ``Nguyễn``.
        """
        words = re.findall(r"\w+|\W+", original)
        alternatives = re.findall(r"\w+", candidate)
        position = 0
        for index, word in enumerate(words):
            if not word.isalpha():
                continue
            for offset in range(position, min(position + 4, len(alternatives))):
                alternative = alternatives[offset]
                original_folded = cls._fold(word)
                alternative_folded = cls._fold(alternative)
                similarity = SequenceMatcher(None, original_folded, alternative_folded).ratio()
                exact = original_folded == alternative_folded
                has_accents = any(ord(c) > 127 for c in alternative)
                alternative_letters = iter(alternative_folded)
                preserves_letters = all(letter in alternative_letters for letter in original_folded)
                protected_acronym = word.isupper() and len(word) <= 3
                repairs_dropped_letters = (
                    min(len(original_folded), len(alternative_folded)) >= 4
                    and 0 <= len(alternative_folded) - len(original_folded) <= 2
                    and original_folded[:1] == alternative_folded[:1]
                    and similarity >= 0.82
                    and preserves_letters
                )
                repairs_short_vietnamese_word = (
                    has_accents
                    and original_folded[:1] == alternative_folded[:1]
                    and 0 <= len(alternative_folded) - len(original_folded) <= 1
                    and similarity >= 0.65
                    and preserves_letters
                    and not protected_acronym
                )
                if exact or (allow_letter_repairs and (repairs_dropped_letters or repairs_short_vietnamese_word)):
                    is_more_complete = len(alternative_folded) > len(original_folded)
                    if has_accents or is_more_complete:
                        if word.isupper():
                            alternative = alternative.upper()
                        elif word[:1].isupper():
                            alternative = alternative[:1].upper() + alternative[1:]
                        words[index] = alternative
                    position = offset + 1
                    break
            else:
                # High-confidence detector labels may omit vowels (vit/bng)
                # that we deliberately leave unchanged. Still consume their
                # aligned word so later proper-name accents can use real ink
                # evidence instead of being stranded outside the lookahead.
                if advance_unmatched:
                    position = min(position + 1, len(alternatives))
        return "".join(words)

    @staticmethod
    def _split_long_crop(crop):
        """Keep line tiles within model width and its 128-character decoder.

        Split only at a real whitespace column. A continuous identifier or
        an unbroken word is left intact rather than cutting through glyphs.
        """
        import cv2
        import numpy as np

        height, width = crop.shape[:2]
        if width <= height * 14:
            return [crop]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, foreground = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        # An empty column can be the tiny gap between two letters of a word.
        # Require a word-sized whitespace run, otherwise "TY" becomes "T Y".
        empty = (foreground > 0).sum(axis=0) == 0
        edges = np.diff(np.r_[False, empty, False].astype(np.int8))
        starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
        minimum_gap = max(3, int(round(height * .16)))
        spaces = [
            (int(left) + int(right)) // 2
            for left, right in zip(starts, ends)
            if right - left >= minimum_gap and width * .3 <= (left + right) / 2 <= width * .7
        ]
        if not spaces:
            return [crop]
        split = min(spaces, key=lambda column: abs(column - width / 2))
        return (VietnameseLineRefiner._split_long_crop(crop[:, :split])
                + VietnameseLineRefiner._split_long_crop(crop[:, split:]))

    @staticmethod
    def _rectified_crop(image, box, *, padding=0):
        """Rectify the detected quadrilateral before recognizing a tilted row."""
        import cv2
        import numpy as np

        points = np.asarray(box, dtype=np.float32)
        if points.shape != (4, 2) or not np.isfinite(points).all():
            return None
        if padding:
            across = ((points[1] - points[0]) + (points[2] - points[3])) / 2
            down = ((points[3] - points[0]) + (points[2] - points[1])) / 2
            across_length, down_length = np.linalg.norm(across), np.linalg.norm(down)
            if across_length < 2 or down_length < 2:
                return None
            horizontal = across / across_length * max(2, down_length * padding)
            vertical = down / down_length * max(2, down_length * padding)
            points += np.array([-horizontal - vertical, horizontal - vertical,
                                horizontal + vertical, -horizontal + vertical], dtype=np.float32)
        width = int(round(max(np.linalg.norm(points[1] - points[0]), np.linalg.norm(points[2] - points[3]))))
        height = int(round(max(np.linalg.norm(points[3] - points[0]), np.linalg.norm(points[2] - points[1]))))
        if width < 2 or height < 2:
            return None
        destination = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
        transform = cv2.getPerspectiveTransform(points, destination)
        return cv2.warpPerspective(image, transform, (width, height), flags=cv2.INTER_CUBIC,
                                   borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    def refine(self, image, lines, *, padding=0.0):
        self.address_candidates = {}
        if not self.weights.is_file():
            return lines
        from PIL import Image
        crops, indices, tile_counts = [], [], []
        address_crops, address_indices, address_tile_counts = [], [], []
        in_address = False
        in_name = False
        for index, (box, text, score) in enumerate(lines):
            folded = self._fold(text)
            other_name_label = folded.startswith("ten") and any(
                marker in folded for marker in ("ngoai", "foreign", "viettat", "vittat", "vittt")
            )
            if other_name_label or folded.startswith(("2", "3", "4", "maso", "dienthoai", "email", "thudientu")):
                in_name = False
            elif folded.startswith(("1ten", "tencongty", "tendoanhnghiep", "tendiadiem", "tendiadim")):
                in_name = True
            if self.looks_like_address_label(text) and folded.startswith(("2", "diachi", "djachi", "dachi", "dach")):
                in_address = True
                in_name = False
            elif folded.startswith(("dienthoai", "dinthoi", "dinthoai", "sofax", "fax", "thudientu", "email", "website")) or re.match(
                r"^\s*[34]\s*[.)]", text
            ):
                in_address = False
            relevant_keyword = any(
                word in folded
                for word in (
                    "congty", "doanhnghiep", "chinhanh", "thuongmai", "dichvu",
                    "diadiemkinhdoanh", "diadimkinhdoanh", "dadimkinhdoanh",
                    "diachi", "djachi", "dachi", "dach",
                )
            )
            if other_name_label or not (in_address or in_name or relevant_keyword):
                continue
            if len(text) < 8 or "@" in text or sum(c.isalpha() for c in text) < 6:
                continue
            crop = self._rectified_crop(image, box, padding=padding)
            if crop is not None and crop.size:
                tiles = self._split_long_crop(crop)
                crops.extend(Image.fromarray(tile[:, :, ::-1]) for tile in tiles)
                indices.append(index)
                tile_counts.append(len(tiles))
                if in_address and not self.looks_like_address_label(text):
                    padded = self._rectified_crop(image, box, padding=.14)
                    if padded is not None and padded.size:
                        tiles = self._split_long_crop(padded)
                        address_crops.extend(Image.fromarray(tile[:, :, ::-1]) for tile in tiles)
                        address_indices.append(index)
                        address_tile_counts.append(len(tiles))
        if not crops:
            return lines
        predictor = self._load()
        result = list(lines)
        all_texts, all_scores = [], []
        for start in range(0, len(crops), 4):
            texts, scores = predictor.predict_batch(crops[start:start+4], return_prob=True)
            all_texts.extend(texts)
            all_scores.extend(scores)
        offset = 0
        for index, count in zip(indices, tile_counts):
            text = " ".join(all_texts[offset:offset + count])
            score = min(all_scores[offset:offset + count])
            offset += count
            box, original, original_score = lines[index]
            if self.accept(original, text, score):
                restored = self.restore_accents(original, text, allow_letter_repairs=float(original_score) < .90,
                                                advance_unmatched=bool(padding))
                if padding and score >= .90 and self._safe_photo_spacing(original, text):
                    restored = text
                # Confidence belongs to the full candidate; do not give a
                # partially restored line a higher score than the detector.
                confidence = float(score) if self._fold(restored) == self._fold(text) else original_score
                result[index] = (box, restored, confidence)
        # A row-wide CTC score can be high even when one word lost a vowel.
        # Keep an independent, padded image reading for later cross-engine
        # validation. It is never applied here without that corroboration.
        if address_crops:
            try:
                texts, scores = [], []
                for start in range(0, len(address_crops), 4):
                    batch_texts, batch_scores = predictor.predict_batch(address_crops[start:start+4], return_prob=True)
                    texts.extend(batch_texts)
                    scores.extend(batch_scores)
                offset = 0
                for index, count in zip(address_indices, address_tile_counts):
                    candidate = " ".join(texts[offset:offset + count])
                    score = min(scores[offset:offset + count])
                    offset += count
                    original = lines[index][1]
                    candidate = self._preserve_identifiers(original, candidate)
                    if score >= .88 and self.accept(original, candidate, score):
                        self.address_candidates[index] = candidate
            except Exception:
                # Optional address rereading must not discard normal results.
                self.address_candidates = {}
        return result

    @classmethod
    def _safe_photo_spacing(cls, original, candidate):
        """Accept actual crop spacing/marks only, with every identifier protected.

        A photographed `128duong` may be reread as `128 đường`. This never
        guesses a boundary from a dictionary: both image readers must agree on
        all folded letters, digits and punctuation, at high crop confidence.
        """
        if cls._fold(original) != cls._fold(candidate):
            return False
        return cls._photo_identifiers_preserved(original, candidate)

    @staticmethod
    def _photo_identifiers_preserved(original, candidate):
        if re.findall(r"\d+", original) != re.findall(r"\d+", candidate):
            return False
        if re.sub(r"[\w\s]", "", original) != re.sub(r"[\w\s]", "", candidate):
            return False
        for token in re.findall(r"\w+(?:[./-]\w+)*", original):
            if not any(char.isdigit() for char in token):
                continue
            # Only this clearly labelled boundary may change spaces. Keep
            # house/unit tokens such as 79/J4, 128A, D18, and 07-02 intact.
            if re.fullmatch(r"\d+(?:duong|đường|phuong|phường)", token, re.IGNORECASE):
                continue
            if re.search(r"(?<!\w)" + re.escape(token) + r"(?!\w)", candidate, re.IGNORECASE) is None:
                return False
        return True

    def corroborate_photo_addresses(self, lines, probe_text):
        """Use a padded crop only if the other engine saw the same full letters.

        RapidOCR's quick photo probe and VietOCR's independently padded crop
        must agree; the PP-OCR line alone never authorizes restoring letters.
        """
        evidence = self._fold(probe_text)
        result = list(lines)
        for index, candidate in self.address_candidates.items():
            if not 0 <= index < len(lines):
                continue
            box, original, score = lines[index]
            canonical = self._fold(candidate)
            if len(canonical) >= 12 and canonical in evidence and self._photo_identifiers_preserved(original, candidate):
                result[index] = (box, candidate, score)
        return result

    @staticmethod
    def _preserve_identifiers(original, candidate):
        """Keep digit-bearing tokens when an aligned language read says O for 0."""
        pattern = re.compile(r"\w+(?:[./-]\w+)*")
        originals, alternatives = list(pattern.finditer(original)), list(pattern.finditer(candidate))
        if len(originals) != len(alternatives):
            return candidate
        for before, after in reversed(list(zip(originals, alternatives))):
            if any(character.isdigit() for character in before.group()):
                candidate = candidate[:after.start()] + before.group() + candidate[after.end():]
        return candidate
