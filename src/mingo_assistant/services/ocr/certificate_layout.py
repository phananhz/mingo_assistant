"""Recover certificate reading order from OCR geometry without guessing text."""
from __future__ import annotations

from math import atan2, cos, isfinite, sin
from statistics import median
from typing import Any


def certificate_lines(lines: list[tuple[Any, str, float]]) -> list[str]:
    """Join nearby fragments on one baseline, retaining separate form columns.

    OCR detectors can return a label and its value as independent boxes in the
    wrong order. Project centers onto the dominant text baseline before sorting
    so a small page skew does not put a right-hand value above its own label.
    Missing/invalid geometry keeps the original OCR order as a safe fallback.
    """
    entries = []
    angles = []
    for box, text, _score in lines:
        try:
            points = [(float(point[0]), float(point[1])) for point in box]
            if len(points) != 4 or not all(isfinite(value) for point in points for value in point):
                raise ValueError("Invalid quadrilateral")
            angle = atan2(points[1][1] - points[0][1], points[1][0] - points[0][0])
            if abs(angle) < 0.21:
                angles.append(angle)
            entries.append((points, str(text).strip()))
        except (TypeError, ValueError, IndexError):
            return [str(text).strip() for _box, text, _score in lines if str(text).strip()]
    angle = median(angles) if angles else 0.0
    cosine, sine = cos(angle), sin(angle)
    boxes = []
    for points, text in entries:
        if not text:
            continue
        xs = [x * cosine + y * sine for x, y in points]
        ys = [-x * sine + y * cosine for x, y in points]
        height = max(ys) - min(ys)
        if height <= 0 or max(xs) <= min(xs):
            return [str(text).strip() for _box, text, _score in lines if str(text).strip()]
        boxes.append((min(xs), max(xs), (min(ys) + max(ys)) / 2, height, text))
    rows: list[list[tuple[float, float, float, float, str]]] = []
    for entry in sorted(boxes, key=lambda item: (item[2], item[0])):
        if rows and abs(entry[2] - median(item[2] for item in rows[-1])) <= 0.45 * min(
            entry[3], median(item[3] for item in rows[-1])
        ):
            rows[-1].append(entry)
        else:
            rows.append([entry])
    result = []
    for row in rows:
        previous = None
        for entry in sorted(row):
            left, right, _center, height, text = entry
            # A second label (e.g. Fax:) is an independent field even if it is
            # close to Phone:. Large gaps denote independent header columns.
            punctuation = text in {":", ",", ";", "."}
            # Font spans may overlap slightly through kerning. A separate
            # colon belongs to the caption, while Fax: after Phone: does not.
            caption_tail = previous is not None and text.endswith(":") and ":" not in result[-1]
            joinable = ":" not in text or punctuation or caption_tail
            if previous is not None and joinable and -.25 * min(height, previous[3]) <= left - previous[1] <= 2.0 * min(height, previous[3]):
                result[-1] += ("" if punctuation else " ") + text
            else:
                result.append(text)
            previous = entry
    return result
