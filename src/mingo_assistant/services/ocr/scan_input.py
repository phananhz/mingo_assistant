"""Temporary, local format adapters; uploaded documents are never modified."""
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz
from PIL import Image, ImageOps, UnidentifiedImageError


@contextmanager
def certificate_pdf(path: str, progress_callback=None):
    if Path(path).suffix.lower() == ".pdf":
        yield path
        return
    with TemporaryDirectory(prefix="min-scan-") as directory:
        target = Path(directory) / "certificate.pdf"
        try:
            with Image.open(path) as source, fitz.open() as document:
                frames = getattr(source, "n_frames", 1)
                if frames > 12:
                    raise ValueError("Ảnh có quá nhiều trang. Vui lòng chia thành các tài liệu tối đa 12 trang.")
                for index in range(frames):
                    if progress_callback:
                        progress_callback(5, f"Đang chuẩn hóa ảnh tài liệu {index + 1}/{frames}")
                    source.seek(index)
                    if source.width * source.height > 48_000_000:
                        raise ValueError("Ảnh quá lớn để xử lý an toàn. Vui lòng dùng ảnh dưới 48 megapixel.")
                    # Camera JPEGs often store orientation in EXIF, not pixels.
                    # Never rewrite that original or flatten transparent ink to black.
                    if source.format == "JPEG":
                        source.draft("RGB", (3600, 3600))
                    frame = ImageOps.exif_transpose(source)
                    frame.thumbnail((3600, 3600), Image.Resampling.LANCZOS)
                    rgba = frame.convert("RGBA")
                    image = Image.new("RGB", rgba.size, "white")
                    image.paste(rgba, mask=rgba.getchannel("A"))
                    stream = BytesIO()
                    image.save(stream, format="PNG")
                    # Stable physical size lets OCR render fine marks instead of
                    # shrinking camera images based on their arbitrary DPI tags.
                    scale = 842.0 / max(image.size)
                    page = document.new_page(width=image.width * scale, height=image.height * scale)
                    page.insert_image(page.rect, stream=stream.getvalue())
                document.save(target)
        except (UnidentifiedImageError, Image.DecompressionBombError) as exc:
            raise ValueError("Không đọc được ảnh tài liệu hoặc ảnh vượt giới hạn an toàn.") from exc
        yield str(target)


@contextmanager
def identity_images(paths: list[str]):
    with TemporaryDirectory(prefix="min-identity-") as directory:
        images = []
        for index, path in enumerate(paths):
            if Path(path).suffix.lower() != ".pdf":
                images.append(path)
                continue
            with fitz.open(path) as document:
                for page_index, page in enumerate(document):
                    target = Path(directory) / f"{index}-{page_index}.png"
                    scale = min(4.0, 2400 / max(page.rect.width, page.rect.height, 1))
                    page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).save(str(target))
                    images.append(str(target))
        yield images
