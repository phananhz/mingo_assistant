"""Conservative geometry recovery for photographed ERC/BRC, never text repair."""
from __future__ import annotations

import cv2
import numpy as np


def _page_quad(color):
    """Only trust a large, bright, four-corner page separated from its background."""
    ratio = min(1.0, 1100 / max(color.shape[:2]))
    small = cv2.resize(color, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = gray.shape
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        area = cv2.contourArea(contour) / (width * height)
        if not .45 < area < .94:
            continue
        polygon = cv2.approxPolyDP(contour, .02 * cv2.arcLength(contour, True), True)
        if len(polygon) != 4 or not cv2.isContourConvex(polygon):
            continue
        points = polygon.reshape(4, 2).astype(np.float32)
        # A page crossing the image boundary cannot be safely reconstructed.
        if (points[:, 0].min() < 3 or points[:, 1].min() < 3
                or points[:, 0].max() > width - 4 or points[:, 1].max() > height - 4):
            continue
        center = points.mean(axis=0)
        points = points[np.argsort(np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0]))]
        points = np.roll(points, -int(np.argmin(points.sum(axis=1))), axis=0)
        edges = np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)
        if min(edges) < min(width, height) * .30 or max(edges) / min(edges) > 2.3:
            continue
        # Expand outward so edge text/accents are not trimmed by the contour.
        return (center + (points - center) * 1.015) / ratio
    return None


def _deskew(color):
    """Vote with long text baselines; page corners/stamps alone cannot rotate ink."""
    gray = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
    ratio = min(1.0, 1500 / max(gray.shape))
    small = cv2.resize(gray, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_AREA)
    edges = cv2.Canny(small, 60, 160)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 1800, 55,
                            minLineLength=max(50, small.shape[1] // 8), maxLineGap=14)
    if lines is None:
        return color
    angles = []
    for x1, y1, x2, y2 in lines[:, 0]:
        angle = float(np.degrees(np.arctan2(float(y2 - y1), float(x2 - x1))))
        if abs(angle) <= 12:
            angles.append(angle)
    if len(angles) < 5:
        return color
    angle = float(np.median(angles))
    agreement = np.mean(np.abs(np.asarray(angles) - angle) < 1.0)
    if not .5 < abs(angle) < 10 or agreement < .65:
        return color
    height, width = color.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
    cosine, sine = abs(matrix[0, 0]), abs(matrix[0, 1])
    new_width, new_height = int(height * sine + width * cosine), int(height * cosine + width * sine)
    matrix[0, 2] += (new_width - width) / 2
    matrix[1, 2] += (new_height - height) / 2
    return cv2.warpAffine(color, matrix, (new_width, new_height), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))


def geometry_variant(image_bytes: bytes) -> bytes | None:
    """An extra candidate only: the normal pipeline still reads the uncropped image."""
    color = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if color is None:
        return None
    quad = _page_quad(color)
    corrected = color
    if quad is not None:
        top_left, top_right, bottom_right, bottom_left = quad
        width = int(max(np.linalg.norm(top_right - top_left), np.linalg.norm(bottom_right - bottom_left)))
        height = int(max(np.linalg.norm(bottom_left - top_left), np.linalg.norm(bottom_right - top_right)))
        destination = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
        corrected = cv2.warpPerspective(color, cv2.getPerspectiveTransform(quad, destination), (width, height),
                                        flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    corrected = _deskew(corrected)
    if corrected is color:
        return None
    ok, data = cv2.imencode(".png", corrected)
    return data.tobytes() if ok else None
