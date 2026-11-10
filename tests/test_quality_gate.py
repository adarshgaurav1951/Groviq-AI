"""
Unit tests for ImageQualityGate.
Verifies blur rejection, glare saturation thresholding, and produce isolation.
"""

import numpy as np
from PIL import Image, ImageFilter
from ml.src.quality import ImageQualityGate


def test_sharp_image_passes():
    qg = ImageQualityGate()
    # Create sharp synthetic checkerboard image
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    arr[::10, :] = 200
    arr[:, ::10] = 200
    img = Image.fromarray(arr)

    res = qg.evaluate(img)
    assert res["is_usable"] is True
    assert res["blur_score"] > qg.blur_threshold


def test_blurred_image_rejected():
    qg = ImageQualityGate()
    # Uniform smooth gradient with Gaussian blur
    arr = np.linspace(50, 150, 10000, dtype=np.uint8).reshape((100, 100))
    arr = np.stack([arr]*3, axis=-1)
    img = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=5))

    res = qg.evaluate(img)
    assert res["is_usable"] is False
    assert "blurry" in res["reason"].lower()


def test_glare_image_rejected():
    qg = ImageQualityGate(glare_max_ratio=0.15)
    # Image with > 20% saturated white pixels (>245)
    arr = np.ones((100, 100, 3), dtype=np.uint8) * 100
    arr[:30, :30] = 255  # 900 / 10000 = 9%
    arr[50:70, 50:70] = 255  # 400 / 10000 = 4%
    arr[10:40, 60:90] = 255  # 900 / 10000 = 9% -> Total 22% glare
    img = Image.fromarray(arr)

    res = qg.evaluate(img)
    assert res["is_usable"] is False
    assert "glare" in res["reason"].lower()

