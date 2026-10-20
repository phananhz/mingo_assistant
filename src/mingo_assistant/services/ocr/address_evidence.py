"""Conservative corroboration of an address reread from the document image.

This module contains no place-name dictionary or OCR model.  It only compares
the supplied image readings and retains their independently agreed tokens.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


_TOKEN = re.compile(r"[^\W_]+(?:[./-][^\W_]+)*", re.UNICODE)


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _compact(value: str) -> str:
    return "".join(_fold(value).split())


def _parts(value: str) -> list[str]:
    return [part.strip() for part in unicodedata.normalize("NFC", value).split(",") if part.strip()]


def _identifiers(value: str) -> list[str]:
    # Preserve separators too: 50-52, P5.09 and 10/3/242 are distinct from
    # 5052, P5/09 and 10/3242 even when their digit sequences look similar.
    return [match.group().casefold() for match in _TOKEN.finditer(value)
            if any(character.isdigit() for character in match.group())]


def _family(source: str) -> str:
    source = source.removesuffix("_enhanced")
    return {"primary": "ppocr_v6", "raw_primary": "ppocr_v6", "legacy": "rapidocr"}.get(source, source)


@dataclass(frozen=True)
class _Reading:
    family: str
    parts: list[str]


def _retain_agreed_tokens(candidate: str, primary: str, legacy: str) -> str:
    """Let two identical independent readings veto a changed token."""
    candidate_tokens = list(_TOKEN.finditer(candidate))
    primary_tokens = _TOKEN.findall(primary)
    legacy_tokens = _TOKEN.findall(legacy)
    if len(candidate_tokens) != len(primary_tokens) or len(primary_tokens) != len(legacy_tokens):
        return candidate
    replacements = {
        match.start(): original
        for match, original, other in zip(candidate_tokens, primary_tokens, legacy_tokens)
        if original.casefold() == other.casefold()
    }
    return _TOKEN.sub(lambda match: replacements.get(match.start(), match.group()), candidate)


def _ir_visual_match(reference: str, candidate: str) -> bool:
    """Allow only an OCR 'ir' at the exact position of a candidate ư vowel."""
    source = _compact(reference)
    target: list[tuple[str, bool]] = []
    for character in candidate:
        if character.isspace():
            continue
        decomposed = unicodedata.normalize("NFD", character.casefold())
        is_horn_u = decomposed.startswith("u") and "\u031b" in decomposed
        target.extend((folded, is_horn_u) for folded in _fold(character))
    left = right = changes = 0
    while left < len(source) and right < len(target):
        character, is_horn_u = target[right]
        if source[left] == character:
            left += 1
            right += 1
        elif source[left:left + 2] == "ir" and character == "u" and is_horn_u:
            left += 2
            right += 1
            changes += 1
        else:
            return False
    return changes > 0 and left == len(source) and right == len(target)


def _preserves_words(reference: str, candidate: str) -> bool:
    """Support missing letters within words, never a missing complete word."""
    words = _TOKEN.findall(reference)
    alternatives = _TOKEN.findall(candidate)
    if len(words) != len(alternatives):
        return False
    for word, alternative in zip(words, alternatives):
        available = iter(_fold(alternative))
        if not all(character in available for character in _fold(word)):
            return False
    return True


def corroborated_address(
    candidate: str,
    readings: list[tuple[str, str]],
    *,
    raw_primary: str = "",
    legacy: str = "",
) -> str | None:
    """Return a supported image reread, or ``None`` when evidence is insufficient.

    Callers must supply extracted addresses, with known caption repairs already
    applied. Both independent image engines must have read the address. PDF
    text can support a component but cannot replace either image reading.
    """
    candidate_parts = _parts(candidate)
    primary_parts = _parts(raw_primary)
    legacy_parts = _parts(legacy)
    if not candidate_parts or not primary_parts or not legacy_parts:
        return None
    count = len(candidate_parts)
    if count not in (len(primary_parts), len(legacy_parts)):
        return None

    if len(primary_parts) == count == len(legacy_parts):
        candidate_parts = [
            _retain_agreed_tokens(part, primary, other)
            for part, primary, other in zip(candidate_parts, primary_parts, legacy_parts)
        ]

    evidence = [_Reading("ppocr_v6", primary_parts), _Reading("rapidocr", legacy_parts)]
    evidence.extend(_Reading(_family(source), _parts(text)) for source, text in readings if text.strip())
    evidence = [reading for reading in evidence if len(reading.parts) == count]

    for index, part in enumerate(candidate_parts):
        identifiers = _identifiers(part)
        references = [
            (reading.family, reading.parts[index]) for reading in evidence
            if _identifiers(reading.parts[index]) == identifiers
        ]
        if any(_compact(reference) == _compact(part) for _, reference in references):
            continue
        supported = any(
            _ir_visual_match(reference, part)
            and any(other_family != family and _preserves_words(other, part)
                    for other_family, other in references)
            for family, reference in references
        )
        if not supported:
            return None
    return ", ".join(candidate_parts)
