"""Reuse authorization mapping with the separate tax-code restoration template."""
from mingo_assistant.services.documents.tax_authorization_close_generator import (
    TaxAuthorizationCloseGenerator,
)


class TaxAuthorizationRestoreGenerator(TaxAuthorizationCloseGenerator):
    FILENAME = "Giay uy quyen khoi phuc MST (Thue).docx"
    TEMPLATE_SHA256 = "5a9d72796e59d07f1962ca5ad2f8938b58e9a6f442e380e35190a645f8a9ba2d"
    MISSING_VALUES_MESSAGE = "Chưa đủ thông tin để điền giấy ủy quyền khôi phục mã số thuế."
