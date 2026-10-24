"""Offline synthetic phone-photo OCR check; no runtime profiles or customer data.

PYTHONPATH=src .venv/Scripts/python.exe -B scripts/benchmark_certificate_photos.py
Reports and input photos stay under ignored tmp/. --compare also runs the old
image-to-PDF adapter (no EXIF or photo-specific geometry), using the same engines.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time

import cv2
import fitz
import numpy as np
from PIL import Image

from benchmark_certificate_ocr import FIELDS, character_error_rate, make_fixtures, normalized

ROOT = Path(__file__).resolve().parents[1]


def prepare(output):
    make_fixtures(output, Path("C:/Windows/Fonts/arial.ttf"))
    for kind in ("erc", "brc"):
        source = Image.open(output / f"{kind}_scan.png").convert("RGB")
        if kind == "erc":
            exif = Image.Exif()
            exif[274] = 6
            source.transpose(Image.Transpose.ROTATE_90).save(output / "erc_phone.jpg", quality=90, exif=exif)
        else:
            pixels = np.asarray(source)
            height, width = pixels.shape[:2]
            corners = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
            destination = np.float32([[190, 100], [width + 65, 155], [width + 150, height + 170], [100, height + 80]])
            photo = cv2.warpPerspective(pixels, cv2.getPerspectiveTransform(corners, destination),
                                        (width + 260, height + 260), borderValue=(55, 45, 35))
            # Broad side shadow, never invent/drop characters in the ground truth.
            shade = np.linspace(.56, 1.0, photo.shape[1])[None, :, None]
            photo = np.clip(photo * shade, 0, 255).astype(np.uint8)
            Image.fromarray(photo).save(output / "brc_phone.jpg", quality=88)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "tmp" / "certificate-photo-qa")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--cases", nargs="+", choices=("erc", "brc"), default=["erc", "brc"])
    args = parser.parse_args()
    from mingo_assistant.services.normalization.address_parser import AddressParser
    from mingo_assistant.services.normalization.administrative_place_matcher import AdministrativePlaceMatcher
    from mingo_assistant.services.ocr.certificate_scan import read_certificate
    from mingo_assistant.services.organization_documents.location_certificate_service import LocationCertificateService
    from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentService

    prepare(args.output)
    address = AddressParser(AdministrativePlaceMatcher(ROOT / "assets/administrative_places/vietnam_admin_2025.json"))
    records = []
    for kind in args.cases:
        service_class = OrganizationDocumentService if kind == "erc" else LocationCertificateService
        service = service_class(address_parser=address, bundle_root=ROOT)
        photo = args.output / f"{kind}_phone.jpg"
        for mode in (["before", "after"] if args.compare else ["after"]):
            record = {"case": kind, "mode": mode}
            started = time.perf_counter()
            try:
                if mode == "before":
                    pdf = args.output / f"{kind}_old_adapter.pdf"
                    with fitz.open(photo) as image:
                        pdf.write_bytes(image.convert_to_pdf())
                    result = service.extract_pdf(pdf)
                else:
                    result = read_certificate(service, photo)
                record["result"] = asdict(result)
                record["exact"] = {key: normalized(value) == normalized(result.values.get(key, ""))
                                   for key, value in FIELDS[kind].items()}
                record["cer"] = {key: character_error_rate(value, result.values.get(key, ""))
                                 for key, value in FIELDS[kind].items()}
                print(f"{kind} {mode}: {sum(record['exact'].values())}/{len(FIELDS[kind])} fields exact", flush=True)
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
                print(f"{kind} {mode}: {record['error']}", flush=True)
            record["seconds"] = round(time.perf_counter() - started, 2)
            print(f"  {record['seconds']} seconds", flush=True)
            records.append(record)
            (args.output / "report.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return int(any(record.get("error") or not all(record.get("exact", {}).values())
                   for record in records if record["mode"] == "after"))


if __name__ == "__main__":
    raise SystemExit(main())
