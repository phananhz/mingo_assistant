"""Fill highlighted text in Form 25 without changing its drawing or fixed text."""
from lxml import etree

from mingo_assistant.services.documents.tax_revenue_commitment_generator import (
    TaxRevenueCommitmentGenerator,
)


class TaxRestorationGenerator(TaxRevenueCommitmentGenerator):
    FILENAME = "MS25_Van ban khoi phuc MST.docx"
    TEMPLATE_SHA256 = "aa670ac35ccff5a8c69639d5b6f15287d655abab5b23159aa60afb460b691053"
    MISSING_VALUES_MESSAGE = "Chưa đủ thông tin để điền văn bản khôi phục mã số thuế."
    REQUIRED_KEYS = (
        "tax_company_name", "tax_signing_place", "tax_receiving_authority",
        "tax_registration_number", "tax_address", "tax_restoration_reason", "tax_taxpayer",
    )

    def _apply_values(self, xml, values: dict[str, str]) -> None:
        # The highlighted anchored line in the heading is not an input field.
        runs = xml.xpath(
            "//w:r[w:rPr/w:highlight[@w:val='yellow' or @w:val='green'] and w:t]",
            namespaces=self.NS,
        )
        colors = [run.xpath("w:rPr/w:highlight/@w:val", namespaces=self.NS)[0] for run in runs]
        if colors != ["yellow"] * 7 + ["green", "yellow"]:
            raise ValueError("Cấu trúc vùng nhập của mẫu Word không đúng mapping.")
        replacements = (
            *self._split_company_heading(values["tax_company_name"]),
            values["tax_signing_place"], values["tax_receiving_authority"],
            values["tax_company_name"], values["tax_registration_number"],
            values["tax_address"], values["tax_restoration_reason"], values["tax_taxpayer"],
        )
        for run, value in zip(runs, replacements):
            self._replace_run_text(run, value)
        # The source has empty paragraphs after the signature, including the
        # required paragraph after its table. Their normal line heights can
        # create a completely blank final page when the reason gains a line.
        tails = list(runs[-1].getparent().itersiblings())
        body = xml.find(self.W + "body")
        if body is not None and len(body) >= 2:
            tails.append(body[-2])
        for paragraph in tails:
            if paragraph.tag != self.W + "p" or any(
                child.tag != self.W + "pPr" for child in paragraph
            ):
                continue
            properties = paragraph.find(self.W + "pPr")
            if properties is None:
                properties = etree.SubElement(paragraph, self.W + "pPr")
            spacing = properties.find(self.W + "spacing")
            if spacing is None:
                spacing = etree.Element(self.W + "spacing")
                run_properties = properties.find(self.W + "rPr")
                if run_properties is not None:
                    run_properties.addprevious(spacing)
                else:
                    properties.append(spacing)
            for name, value in {"before": "0", "after": "0", "line": "20", "lineRule": "exact"}.items():
                spacing.set(self.W + name, value)
