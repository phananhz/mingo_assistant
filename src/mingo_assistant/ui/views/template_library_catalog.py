"""Display-only catalog of supplied forms; no file processing or persistence."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateDisplayItem:
    id: str
    title: str
    filename: str
    folder: str

    @property
    def format_label(self) -> str:
        return self.filename.rsplit(".", 1)[-1].upper()


@dataclass(frozen=True)
class TemplateDisplayGroup:
    id: str
    title: str
    description: str
    items: tuple[TemplateDisplayItem, ...]


_DKDN = "Biểu mẫu ĐKDN/Biểu mẫu theo Thông tư 121.2026 mới"
_TAX = "Biểu mẫu Thuế"

TEMPLATE_GROUPS = (
    TemplateDisplayGroup("dkdn", "Biểu mẫu ĐKDN", "Đăng ký và thay đổi thông tin doanh nghiệp", (
        TemplateDisplayItem("dkdn-02", "Thành lập công ty TNHH 1 thành viên", "1. MS2_Thanh lap cong ty TNHH 1 TV.docx", _DKDN),
        TemplateDisplayItem("dkdn-03", "Thành lập công ty TNHH 2 thành viên", "2. MS3_Thanh lap cong ty TNHH 2 TV.docx", _DKDN),
        TemplateDisplayItem("dkdn-04", "Thành lập công ty cổ phần", "3. MS4_Thanh lap CTCP.docx", _DKDN),
        TemplateDisplayItem("dkdn-beneficial", "Danh sách chủ sở hữu hưởng lợi", "4. Danh sach CSH huong loi.docx", _DKDN),
        TemplateDisplayItem("dkdn-12", "Thay đổi nội dung đăng ký doanh nghiệp", "5. MS 12_Thay doi noi dung DKDN.docx", _DKDN),
        TemplateDisplayItem("dkdn-27", "Tạm ngừng kinh doanh, tiếp tục kinh doanh", "6. MS 27_Tam ngung KD, tiep tuc KD.docx", _DKDN),
        TemplateDisplayItem("dkdn-30", "Thông báo giải thể", "7. MS30_Thong bao giai the.docx", _DKDN),
    )),
    TemplateDisplayGroup("tax", "Biểu mẫu thuế", "Cam kết, ủy quyền và thủ tục mã số thuế", (
        TemplateDisplayItem("tax-commitment", "Cam kết chung khi chấm dứt mã số thuế", "Cam ket chung khi cham dut MST.docx", _TAX),
        TemplateDisplayItem("tax-revenue", "Cam kết chưa phát sinh doanh thu, nghĩa vụ khác", "Cam ket_chua phat sinh doanh thu, nghia vu khac.docx", _TAX),
        TemplateDisplayItem("tax-ecommerce", "Cam kết không có hoạt động thương mại điện tử", "Cam ket_khong co hoat dong TMĐT.docx", _TAX),
        TemplateDisplayItem("tax-invoice", "Cam kết không phát hành hóa đơn", "Cam ket_khong phat hanh hoa don.docx", _TAX),
        TemplateDisplayItem("tax-refund", "Công văn từ chối hoàn tiền", "Cong van_tu choi hoan tien_MS01.ĐNKHT TT 89.2026.docx", _TAX),
        TemplateDisplayItem("tax-authorization-close", "Giấy ủy quyền giải thể (thuế)", "Giay uy quyen giai the (Thue).doc", _TAX),
        TemplateDisplayItem("tax-authorization-restore", "Giấy ủy quyền khôi phục mã số thuế", "Giay uy quyen khoi phuc MST (Thue).doc", _TAX),
        TemplateDisplayItem("tax-24", "Văn bản chấm dứt mã số thuế", "MS 24_Van ban cham dut MST.docx", _TAX),
        TemplateDisplayItem("tax-25", "Văn bản khôi phục mã số thuế", "MS25_Van ban khoi phuc MST.docx", _TAX),
        TemplateDisplayItem("tax-customs", "Văn bản xác nhận không nợ thuế hải quan", "VB xac nhan_khong no thue Hai quan.docx", _TAX),
    )),
)
