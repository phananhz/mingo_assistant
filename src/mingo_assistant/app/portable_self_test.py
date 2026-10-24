"""Runtime verification for the portable Windows build.

This module is intentionally callable from the frozen, windowed executable so
the release script can prove that lazy OCR imports, native DLLs, and bundled
model files all work after PyInstaller extraction.
"""
from __future__ import annotations

import importlib
import hashlib
import json
import os
import socket
import sys
import tempfile
import traceback
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any


OCR_MODELS = (
    "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
    "PP-OCRv6_det_small.onnx",
    "PP-OCRv6_rec_medium.onnx",
    "vietocr_vgg_transformer.pth",
)

QR_MODELS = (
    "detect.prototxt",
    "detect.caffemodel",
    "sr.prototxt",
    "sr.caffemodel",
)


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[3]


def _check_file(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": path.is_file(), "size": path.stat().st_size if path.is_file() else 0}


def _verify_authorized_profiles(root: Path, working: Path, seed_file: Path | None = None) -> dict[str, Any]:
    """Verify a clean-machine import and actual dropdown autofill, without logging PII."""
    from PySide6.QtWidgets import QApplication

    from mingo_assistant.application.profiles import AuthorizedPersonUseCases
    from mingo_assistant.repositories.authorized_person_repository import AuthorizedPersonProfileRepository
    from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace
    from mingo_assistant.ui.views.location_business_workspace import LocationBusinessWorkspace
    from mingo_assistant.ui.views.location_business_termination_workspace import LocationBusinessTerminationWorkspace

    seed = seed_file or root / "assets/defaults/authorized_person_seed.json"
    if not seed.is_file():
        raise RuntimeError("The EXE is missing its authorized-person profile resource.")
    expected_payload = json.loads(seed.read_text(encoding="utf-8"))
    expected = expected_payload.get("profiles", [])
    if not expected or any(AuthorizedPersonProfileRepository._is_legacy_sample(profile) for profile in expected):
        raise RuntimeError("The EXE contains empty or sample authorized-person profiles.")
    local_file = working / "authorized-profile-appdata/authorized_person.json"
    if local_file.exists():
        raise RuntimeError("Authorized-profile verification requires fresh local data.")
    repository = AuthorizedPersonProfileRepository(
        local_file, root / "assets/defaults/authorized_person_profiles.json", seed_file=seed,
    )
    defaults = AuthorizedPersonUseCases(repository).selected()
    if defaults["__profiles"] != expected or not local_file.is_file():
        raise RuntimeError("The EXE did not initialize all authorized-person profiles on a new machine.")
    app = QApplication.instance() or QApplication([])
    checks = 0
    for workspace_type in (BusinessRegistrationWorkspace, LocationBusinessWorkspace, LocationBusinessTerminationWorkspace):
        workspace = workspace_type(
            on_back=lambda: None, on_save=lambda case: None, bundle_root=root,
            default_export_root=working, authorized_person_defaults=defaults,
        )
        try:
            selector = workspace.person_fill_selectors["authorized_person"]
            if selector.count() != len(expected) + 1:
                raise RuntimeError("The packaged authorized-person dropdown has missing or unexpected profiles.")
            for index, profile in enumerate(expected):
                option = selector.findData(f"authorized_profile:{index}")
                if option < 0:
                    raise RuntimeError("A bundled profile is absent from the packaged dropdown.")
                selector.setCurrentIndex(option)
                selector.activated.emit(option)
                for key, value in profile.items():
                    if key.startswith("authorized_person_") and key in workspace.fields:
                        if workspace._field_value(key) != str(value or ""):
                            raise RuntimeError(f"Packaged profile {index + 1} did not autofill field {key}.")
                checks += 1
        finally:
            workspace.close()
            workspace.deleteLater()
            app.processEvents()
    return {"profiles": len(expected), "autofill_checks": checks, "autofill_verified": True,
            "fresh_install": True, "bundle_sha256": hashlib.sha256(seed.read_bytes()).hexdigest()}


@contextmanager
def _offline_runtime():
    """Forbid Python network connects without changing the machine's network."""
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create = socket.create_connection

    def blocked(*args, **kwargs):
        raise RuntimeError("Network access is disabled during portable verification.")

    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked
    try:
        yield
    finally:
        socket.socket.connect = original_connect
        socket.socket.connect_ex = original_connect_ex
        socket.create_connection = original_create


def _verify_pdf_and_update_workflow(root: Path, working: Path) -> dict[str, Any]:
    """Exercise bundled PDF reading and the updated form-to-DOCX data path."""
    import fitz
    from docx import Document
    from PySide6.QtWidgets import QApplication

    from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentService
    from mingo_assistant.services.organization_documents.location_certificate_service import LocationCertificateService
    from mingo_assistant.services.documents.dependent_unit_generator import DependentUnitTemplateGenerator
    from mingo_assistant.ui.views.location_business_update_workspace import LocationBusinessUpdateWorkspace

    company = "CONG TY TNHH PORTABLE TEST"
    common = ["Ma so doanh nghiep: 0312345678", "Ten cong ty viet bang tieng Viet: " + company,
              "2. Dia chi tru so chinh: So 1 duong Mau, Phuong 5, Thanh pho Ho Chi Minh, Viet Nam"]
    texts = {
        "erc": "\n".join(["GIAY CHUNG NHAN DANG KY DOANH NGHIEP", *common]),
        "brc": "\n".join([
            "GIAY CHUNG NHAN DANG KY DIA DIEM KINH DOANH", "Ma so dia diem kinh doanh: 00001",
            "1. Ten dia diem kinh doanh: DIA DIEM KINH DOANH - " + company,
            "2. Dia chi: So 1 duong Mau, Phuong 5, Thanh pho Ho Chi Minh, Viet Nam",
            "3. Thong tin ve nguoi dung dau", "4. Thong tin ve doanh nghiep/chi nhanh chu quan:",
            "Ten doanh nghiep/chi nhanh: " + company, "Ma so doanh nghiep/chi nhanh: 0312345678",
        ]),
    }
    pdf_checks = {}
    for kind, service in (("erc", OrganizationDocumentService(bundle_root=root)),
                          ("brc", LocationCertificateService(bundle_root=root))):
        path = working / f"{kind}.pdf"
        with fitz.open() as pdf:
            page = pdf.new_page()
            page.insert_text((40, 60), texts[kind], fontsize=8)
            pdf.save(path)
        result = service.extract_pdf(path)
        if result.document_type != kind or result.processing_route != ("pdf_text",):
            raise RuntimeError(f"Bundled {kind.upper()} text-PDF extraction failed.")
        pdf_checks[kind] = {"document_type": result.document_type, "route": result.processing_route}

    app = QApplication.instance() or QApplication([])
    workspace = LocationBusinessUpdateWorkspace(
        on_back=lambda: None, on_save=lambda case: None, bundle_root=root, default_export_root=working,
    )
    try:
        if not workspace.change_option_indicators["change_tax_selected"].isHidden():
            raise RuntimeError("A new update dossier incorrectly marks the empty tax section.")
        if "change_correction_selected" in workspace.fields:
            raise RuntimeError("The retired correction option remains in the packaged UI.")
        workspace.fields["new_location_phone"].setText("0900000001")
        if workspace.change_option_indicators["change_address_selected"].isHidden():
            raise RuntimeError("Entered address/contact data is not marked in the packaged UI.")
        values = workspace.form_values()
        template = root / "assets/templates/word/dependent_units/ddkd_update"
        generator = DependentUnitTemplateGenerator(template, working)
        result = generator.generate(values, "Portable verification", working / "docx")
        notification = next(item.output_path for item in result.generated if item.source_name == "Thong bao thay doi.docx")
        text = "\n".join(p.text for p in generator._iter_paragraphs(Document(notification)))
        folded = generator._fold(text)
        if "0900000001" not in text or "dang ky thay doi dia chi dia diem kinh doanh" not in folded:
            raise RuntimeError("The packaged exporter omitted the populated address section.")
        if any(label in folded for label in ("dang ky thay doi ten dia diem kinh doanh",
                                             "dang ky thay doi thong tin dang ky thue", "de nghi hieu dinh")):
            raise RuntimeError("The packaged exporter retained an empty or retired section.")
        if "Website" not in text:
            raise RuntimeError("The packaged exporter removed blank child fields from a populated section.")
        legacy = dict(workspace.build_case_summary().form_values)
        legacy.pop("location_update_tax_labor_count_entered", None)
        legacy["tax_labor_count"] = "1"
        reopened = LocationBusinessUpdateWorkspace(
            on_back=lambda: None, on_save=lambda case: None, bundle_root=root, default_export_root=working,
            case=replace(workspace.build_case_summary(), form_values=legacy),
        )
        try:
            if reopened.fields["tax_labor_count"].text():
                raise RuntimeError("The packaged UI restored the legacy automatic labor count.")
            if not reopened.change_option_indicators["change_tax_selected"].isHidden():
                raise RuntimeError("The packaged UI marked an empty legacy tax section.")
        finally:
            reopened.close()
            reopened.deleteLater()
            app.processEvents()
        return {"pdf": pdf_checks, "update_form": True, "docx_export": True,
                "legacy_labor_default_ignored": True, "generated_documents": len(result.generated)}
    finally:
        workspace.close()
        workspace.deleteLater()
        app.processEvents()


def _verify_main_window(root: Path, working: Path) -> dict[str, Any]:
    from PySide6.QtWidgets import QApplication

    from mingo_assistant import __version__
    from mingo_assistant.app.container import AppContainer
    from mingo_assistant.app.paths import AppPaths
    from mingo_assistant.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    paths = AppPaths(root, working / "main-app-data", working / "main-exports")
    paths.ensure_user_dirs()
    container = AppContainer.build(paths)
    window = MainWindow(
        app_paths=paths, case_repository=container.case_repository, case_use_cases=container.case_use_cases,
        authorized_person_repository=container.authorized_person_repository,
        authorized_person_use_cases=container.authorized_person_use_cases,
        registration_services=container.registration_services, industry_catalog=container.industry_catalog,
    )
    try:
        window.show()
        app.processEvents()
        expected_title = f"Min Assistant v{__version__}"
        if window.windowTitle() != expected_title or not window.isVisible():
            raise RuntimeError("The packaged main window did not initialize correctly.")
        return {"title": window.windowTitle(), "shown": True, "isolated_app_data": True}
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def run_portable_self_test(report_path: str | Path) -> int:
    report_file = Path(report_path).resolve()
    report_file.parent.mkdir(parents=True, exist_ok=True)
    root = _bundle_root()
    from mingo_assistant import __version__
    report: dict[str, Any] = {"ok": False, "version": __version__, "frozen": bool(getattr(sys, "frozen", False)),
                              "bundle_root": str(root), "executable": sys.executable}

    try:
        with _offline_runtime(), tempfile.TemporaryDirectory(prefix="mingo-portable-", dir=report_file.parent) as temporary:
            return _run_checks(root, report, Path(temporary))
    except BaseException as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["traceback"] = traceback.format_exc()
    finally:
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1


def _run_checks(root: Path, report: dict[str, Any], working: Path) -> int:
    report["network_access"] = "Python socket connects blocked during checks"
    original_appdata = os.environ.get("APPDATA")
    original_platform = os.environ.get("QT_QPA_PLATFORM")
    os.environ["APPDATA"] = str(working / "appdata")
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    try:
        report["authorized_profiles"] = _verify_authorized_profiles(root, working)
        imports = {}
        for module_name in (
            "cv2",
            "numpy",
            "onnxruntime",
            "rapidocr_onnxruntime",
            "torch",
            "torchvision",
            "vietocr",
            "zxingcpp",
            "pyzbar.pyzbar",
        ):
            importlib.import_module(module_name)
            imports[module_name] = True
        report["imports"] = imports

        model_files = [
            *(_check_file(root / "assets" / "models" / "ocr" / name) for name in OCR_MODELS),
            *(_check_file(root / "assets" / "qr_models" / name) for name in QR_MODELS),
        ]
        report["model_files"] = model_files
        if not all(item["exists"] and item["size"] > 0 for item in model_files):
            raise RuntimeError("The portable package is missing one or more OCR/QR model files.")

        import cv2
        import numpy as np
        from PIL import Image
        from rapidocr_onnxruntime import RapidOCR

        from mingo_assistant.services.ocr.vietnamese_document_ocr import VietnameseDocumentOcr
        from mingo_assistant.services.ocr.vietnamese_line_refiner import VietnameseLineRefiner
        from mingo_assistant.services.qr.scanner import IdentityQrScanner

        image = np.full((320, 1200, 3), 255, dtype=np.uint8)
        cv2.putText(image, "OCR 123", (55, 215), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 3, cv2.LINE_AA)
        encoded_ok, encoded = cv2.imencode(".png", image)
        if not encoded_ok:
            raise RuntimeError("Could not create the OCR self-test image.")

        ocr = VietnameseDocumentOcr(root)
        lines = ocr.recognize(encoded.tobytes())
        report["ppocr_v6"] = {"available": ocr.is_available, "lines": lines}
        if "123" not in "".join(text for text, _score in lines):
            raise RuntimeError("PP-OCRv6 did not recognize the self-test digits.")
        legacy_lines, _ = RapidOCR()(encoded.tobytes())
        report["rapidocr"] = {"lines": [[str(line[1]), float(line[2])] for line in legacy_lines or []]}
        if "123" not in "".join(line[0] for line in report["rapidocr"]["lines"]):
            raise RuntimeError("RapidOCR did not recognize the self-test digits.")

        refiner = VietnameseLineRefiner(ocr.model_dir)
        predictor = refiner._load()
        foreground = (cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) < 128).astype(np.uint8)
        x, y, width, height = cv2.boundingRect(cv2.findNonZero(foreground))
        crop = image[max(0, y - 6):y + height + 6, max(0, x - 6):x + width + 6, ::-1]
        refined, confidence = predictor.predict(Image.fromarray(crop), return_prob=True)
        report["vietocr"] = {"weights": _check_file(refiner.weights), "predictor": type(predictor).__name__,
                              "text": refined, "confidence": float(confidence)}
        if "123" not in refined:
            raise RuntimeError("VietOCR did not recognize the self-test digits.")

        qr_scanner = IdentityQrScanner(root)
        payload = "001090000001||NGUYEN VAN TEST|01011990|Nam|Dia chi kiem thu|01012021"
        qr = cv2.QRCodeEncoder_create().encode(payload)
        qr = cv2.copyMakeBorder(qr, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
        qr = cv2.resize(qr, None, fx=6, fy=6, interpolation=cv2.INTER_NEAREST)
        qr = cv2.cvtColor(qr, cv2.COLOR_GRAY2BGR)
        report["qr"] = {
            "wechat_available": qr_scanner._get_wechat_detector() is not None,
            "wechat_decoded": qr_scanner._scan_qr_with_wechat([qr]) == payload,
            "zxingcpp_decoded": qr_scanner._scan_qr_with_zxing([qr]) == payload,
            "pyzbar_decoded": qr_scanner._scan_qr_with_pyzbar([qr]) == payload,
        }
        if not all(report["qr"].values()):
            raise RuntimeError("One or more bundled QR engines failed to decode the self-test QR.")
        report["workflow"] = _verify_pdf_and_update_workflow(root, working)
        report["main_window"] = _verify_main_window(root, working)
        report["ok"] = True
    finally:
        for name, original in (("APPDATA", original_appdata), ("QT_QPA_PLATFORM", original_platform)):
            if original is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = original
    return 0
