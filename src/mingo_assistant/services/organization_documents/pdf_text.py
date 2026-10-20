"""Read certificate PDFs with a broken or absent ToUnicode map.

Some exported certificates display correctly but expose glyph IDs as Unicode
or replacement characters. Recover only from their own embedded font cmap;
never infer a company name, identifier or address from a word dictionary.
"""
from __future__ import annotations

from collections import defaultdict
import unicodedata

import fitz

from mingo_assistant.services.ocr.certificate_layout import certificate_lines


def _damaged(text: str) -> bool:
    controls = sum(ord(character) < 32 and character not in "\n\r\t" for character in text)
    return controls > max(2, len(text) * .02) or text.count("\ufffd") > max(2, len(text) * .01) or text.count("(cid:") >= 3


def _font_key(name: str) -> str:
    return "".join(character for character in name.split("+", 1)[-1].casefold() if character.isalnum())


def _embedded_maps(page, cache: dict[int, dict[int, str]]) -> dict[str, dict[int, str]]:
    fonts: dict[str, list[dict[int, str]]] = defaultdict(list)
    for info in page.get_fonts(full=True):
        xref, _extension, _kind, name = info[:4]
        if xref not in cache:
            try:
                _name, _ext, _type, buffer = page.parent.extract_font(xref)
                if not buffer:
                    cache[xref] = {}
                    continue
                font = fitz.Font(fontbuffer=buffer)
                candidates: dict[int, set[str]] = defaultdict(set)
                for codepoint in font.valid_codepoints():
                    character = chr(codepoint)
                    if character.isspace():
                        character = " "
                    if unicodedata.category(character).startswith("C"):
                        continue
                    glyph = font.has_glyph(codepoint)
                    if glyph:
                        candidates[glyph].add(character)
                cache[xref] = {
                    glyph: next(iter(characters))
                    for glyph, characters in candidates.items()
                    if len(characters) == 1
                }
            except Exception:
                # Unsupported font types remain the responsibility of OCR.
                cache[xref] = {}
        if cache[xref]:
            fonts[_font_key(name)].append(cache[xref])
    result = {}
    for name, maps in fonts.items():
        # Multiple embedded subsets with the same name may assign different
        # characters to one glyph ID. Ambiguous mappings must not be guessed.
        candidates: dict[int, set[str]] = defaultdict(set)
        for mapping in maps:
            for glyph, character in mapping.items():
                candidates[glyph].add(character)
        result[name] = {glyph: next(iter(values)) for glyph, values in candidates.items() if len(values) == 1}
    return result


def _recover_page(page, cache: dict[int, dict[int, str]]) -> str:
    fonts = _embedded_maps(page, cache)
    lines = []
    missing = total = 0
    for span in page.get_texttrace():
        glyphs = span.get("chars", ())
        if not glyphs or span.get("type", 0) == 3:
            continue  # invisible OCR layers must not replace visible content
        broken = sum(char[0] in (0, 65533) for char in glyphs) > len(glyphs) * .1
        mapping = fonts.get(_font_key(span["font"]), {})
        chunks = []
        current = []
        previous_origin = None
        direction = span.get("dir", (1, 0))
        for codepoint, glyph, origin, bounds in glyphs:
            total += 1
            if broken:
                character = mapping.get(glyph)
            else:
                character = chr(codepoint) if 0 < codepoint <= 0x10ffff else None
            if character is None or character == "\ufffd":
                missing += 1
                character = "\ufffd"
            if previous_origin is not None:
                dx, dy = origin[0] - previous_origin[0], origin[1] - previous_origin[1]
                if abs(-dx * direction[1] + dy * direction[0]) > span["size"] * .5:
                    chunks.append(current)
                    current = []
            current.append((character, bounds))
            previous_origin = origin
        if current:
            chunks.append(current)
        for chunk in chunks:
            text = "".join(character for character, _bounds in chunk)
            left = min(bounds[0] for _character, bounds in chunk)
            top = min(bounds[1] for _character, bounds in chunk)
            right = max(bounds[2] for _character, bounds in chunk)
            bottom = max(bounds[3] for _character, bounds in chunk)
            lines.append(([[left, top], [right, top], [right, bottom], [left, bottom]], text, 1.0))
    if not total or missing / total > .01:
        return ""
    text = unicodedata.normalize("NFC", "\n".join(certificate_lines(lines)))
    return text if not _damaged(text) else ""


def extract_certificate_text(document) -> str:
    """Return visible, ordered text, falling back to normal extraction safely."""
    pages = []
    cache: dict[int, dict[int, str]] = {}
    for page in document:
        # PyMuPDF's sorted text can replace corrupt control characters with
        # spaces. Inspect the original text first or that evidence is lost.
        text = page.get_text("text")
        if _damaged(text):
            try:
                recovered = _recover_page(page, cache)
            except Exception:
                recovered = ""
            if recovered:
                text = recovered
        else:
            text = page.get_text("text", sort=True)
        pages.append(text)
    return "\n".join(pages)
