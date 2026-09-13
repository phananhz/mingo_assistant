from __future__ import annotations

import re


class VietnameseMoneyFormatter:
    """Pure VND formatting rules shared by registration workflows."""

    @staticmethod
    def digits(value: str) -> str:
        return re.sub(r"\D", "", value)

    @staticmethod
    def format_digits(digits: str) -> str:
        return f"{int(digits):,}".replace(",", ".")

    def to_words(self, number: int) -> str:
        if number == 0:
            return "không"

        units = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"]
        groups: list[int] = []
        while number:
            groups.append(number % 1000)
            number //= 1000

        parts: list[str] = []
        for index in range(len(groups) - 1, -1, -1):
            group = groups[index]
            if group == 0:
                continue
            words = self.read_three_digits(group, force_hundreds=index < len(groups) - 1)
            unit = units[index] if index < len(units) else ""
            parts.append(" ".join(part for part in (words, unit) if part))
        return " ".join(parts)

    @staticmethod
    def read_three_digits(number: int, force_hundreds: bool = False) -> str:
        digits = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
        hundred = number // 100
        ten = (number % 100) // 10
        one = number % 10
        words: list[str] = []

        if hundred:
            words.extend([digits[hundred], "trăm"])
        elif force_hundreds and (ten or one):
            words.extend(["không", "trăm"])

        if ten > 1:
            words.extend([digits[ten], "mươi"])
            if one == 1:
                words.append("mốt")
            elif one == 5:
                words.append("lăm")
            elif one:
                words.append(digits[one])
        elif ten == 1:
            words.append("mười")
            if one == 5:
                words.append("lăm")
            elif one:
                words.append(digits[one])
        elif one:
            if hundred or force_hundreds:
                words.append("lẻ")
            words.append(digits[one])
        return " ".join(words)
