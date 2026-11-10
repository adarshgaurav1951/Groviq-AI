"""
Image Quality Gate for BarcodeLess Produce Assistant.
Analyzes camera frames for blur, glare, poor illumination, and isolates the produce item.
Ensures unusable or degraded captures do not trigger erratic model inferences.
"""

import numpy as np
from PIL import Image, ImageOps
from typing import Tuple, Dict, Any


class ImageQualityGate:
    def __init__(
        self,
        blur_threshold: float = 70.0,
        glare_max_ratio: float = 0.15,
        min_luminance: float = 30.0,
        max_luminance: float = 245.0,
    ):
        self.blur_threshold = blur_threshold
        self.glare_max_ratio = glare_max_ratio
        self.min_luminance = min_luminance
        self.max_luminance = max_luminance

    def _compute_laplacian_variance(self, gray: np.ndarray) -> float:
        """Computes variance of the discrete 3x3 Laplacian operator."""
        kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
        h, w = gray.shape
        if h < 5 or w < 5:
            return 0.0
        padded = np.pad(gray, ((1, 1), (1, 1)), mode="reflect")
        sub_matrices = np.lib.stride_tricks.sliding_window_view(padded, (3, 3))
        laplacian = np.einsum("ijkl,kl->ij", sub_matrices, kernel)
        return float(np.var(laplacian))

    def evaluate(self, image: Image.Image) -> Dict[str, Any]:
        """
        Evaluates input PIL image against quality metrics:
        - Laplacian blur variance
        - Specular glare / blowout on produce surface vs platter
        - Under/over-exposure
        """
        rgb_img = image.convert("RGB")
        arr = np.array(rgb_img, dtype=np.float32)
        gray_arr = np.mean(arr, axis=-1)

        # 1. Blur evaluation
        blur_score = self._compute_laplacian_variance(gray_arr)

        # 2. Glare evaluation: border-aware white backdrop vs specular blowout
        h, w = gray_arr.shape
        border_pixels = np.concatenate([arr[0, :, :], arr[-1, :, :], arr[:, 0, :], arr[:, -1, :]])
        border_is_white = float(np.mean(np.all(border_pixels >= 240.0, axis=-1))) > 0.50

        overall_saturated = float(np.mean(gray_arr >= 250.0))

        if overall_saturated > 0.85:
            glare_ratio = overall_saturated
            is_glare = True
        elif border_is_white:
            # White backdrop / scale platter detected
            is_bg = np.all(arr >= 242.0, axis=-1)
            fg_pixels = arr[~is_bg]
            if len(fg_pixels) == 0:
                glare_ratio = 1.0
                is_glare = True
            else:
                fg_gray = np.mean(fg_pixels, axis=-1)
                glare_ratio = float(np.mean(fg_gray >= 248.0))
                is_glare = glare_ratio > self.glare_max_ratio
        else:
            # Natural / darker background: evaluate all saturated glare pixels
            glare_ratio = float(np.mean(gray_arr >= 248.0))
            is_glare = glare_ratio > self.glare_max_ratio

        # 3. Luminance evaluation
        mean_luminance = float(np.mean(gray_arr))

        is_usable = True
        reasons = []

        if blur_score < self.blur_threshold:
            is_usable = False
            reasons.append(f"Image is blurry (score {blur_score:.1f} < {self.blur_threshold:.1f}). Please hold item steady.")

        if is_glare:
            is_usable = False
            reasons.append(f"Excessive surface glare detected ({glare_ratio*100:.1f}% saturated). Adjust capture angle or lighting.")

        if mean_luminance < self.min_luminance:
            is_usable = False
            reasons.append(f"Scene is underexposed/too dark (mean luminance {mean_luminance:.1f} < {self.min_luminance:.1f}).")

        if mean_luminance > self.max_luminance and overall_saturated > 0.85:
            is_usable = False
            reasons.append(f"Scene is severely overexposed (mean luminance {mean_luminance:.1f} > {self.max_luminance:.1f}).")

        return {
            "is_usable": is_usable,
            "blur_score": round(blur_score, 2),
            "glare_ratio": round(glare_ratio, 4),
            "mean_luminance": round(mean_luminance, 2),
            "reason": "; ".join(reasons) if reasons else "Image quality passed all checks."
        }

    def isolate_produce(self, image: Image.Image) -> Image.Image:
        """Crops / isolates produce region."""
        w, h = image.size
        if w > 120 and h > 120:
            crop_margin_x = int(w * 0.05)
            crop_margin_y = int(h * 0.05)
            return image.crop((crop_margin_x, crop_margin_y, w - crop_margin_x, h - crop_margin_y))
        return image
