"""
Image Edit Tool — OpenCV filters for Phase 5 editing.
"""
from mcp.base_tool import BaseTool
from typing import Any, Dict
import cv2
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

SHARPEN_KERNEL = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])


def _apply_sepia(img):
    kernel = np.array([[0.272, 0.534, 0.131],
                       [0.349, 0.686, 0.168],
                       [0.393, 0.769, 0.189]])
    return cv2.transform(img, kernel).clip(0, 255).astype(np.uint8)


def _apply_color_shift(img, red=0, green=0, blue=0):
    result = img.copy().astype(np.int16)
    result[:, :, 2] = np.clip(result[:, :, 2] + red, 0, 255)
    result[:, :, 1] = np.clip(result[:, :, 1] + green, 0, 255)
    result[:, :, 0] = np.clip(result[:, :, 0] + blue, 0, 255)
    return result.astype(np.uint8)


FILTERS = {
    "darken": lambda img: cv2.convertScaleAbs(img, alpha=0.35, beta=-60),
    "brighten": lambda img: cv2.convertScaleAbs(img, alpha=1.8, beta=50),
    "warm": lambda img: _apply_color_shift(img, red=40, blue=-30),
    "cool": lambda img: _apply_color_shift(img, red=-30, blue=40),
    "vintage": lambda img: _apply_sepia(img),
    "blur": lambda img: cv2.GaussianBlur(img, (21, 21), 0),
    "sharpen": lambda img: cv2.filter2D(img, -1, SHARPEN_KERNEL),
    "grayscale": lambda img: cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR),
    "contrast": lambda img: cv2.convertScaleAbs(img, alpha=2.0, beta=-30),
    "invert": lambda img: cv2.bitwise_not(img),
}


class ImageEditTool(BaseTool):
    name = "image_editor"
    description = "Apply visual filters to images (darken, brighten, grayscale, etc.)."

    async def execute(self, image_path: str, filter_name: str,
                      output_path: str = "", **kwargs) -> Dict[str, Any]:
        """Apply a named filter to an image."""
        if filter_name not in FILTERS:
            available = ", ".join(FILTERS.keys())
            return {"success": False, "error": f"Unknown filter '{filter_name}'. Available: [{available}]"}

        if not os.path.exists(image_path):
            return {"success": False, "error": f"Image not found: {image_path}"}

        if not output_path:
            base, ext = os.path.splitext(image_path)
            output_path = f"{base}_{filter_name}{ext}"

        img = cv2.imread(image_path)
        filtered = FILTERS[filter_name](img)
        cv2.imwrite(output_path, filtered)

        logger.info(f"Applied filter '{filter_name}' to {image_path} -> {output_path}")
        return {"success": True, "image_path": output_path, "filter": filter_name}
