"""
Produce & General Product Classifier for BarcodeLess Produce Assistant.
Combines pre-trained MobileNetV3 feature extraction (for real-world camera captures)
with prototype matching, open-world recognition, and dynamic new product enrollment.
"""

import os
import json
import numpy as np
import torch
import torchvision.models as models
from PIL import Image
from typing import List, Dict, Any, Tuple, Optional


# Mapping from prominent ImageNet categories to standardized supermarket produce items
IMAGENET_TO_PRODUCE_MAP = {
    "banana": "Banana",
    "orange": "Orange",
    "lemon": "Lemon",
    "Granny Smith": "Apple Granny Smith",
    "strawberry": "Strawberry",
    "bell pepper": "Pepper Green",
    "cucumber": "Cucumber",
    "pineapple": "Pineapple",
    "pomegranate": "Pomegranate",
    "corn": "Corn",
    "acorn squash": "Squash",
    "head cabbage": "Cabbage",
    "broccoli": "Broccoli",
    "cauliflower": "Cauliflower",
    "zucchini": "Zucchini",
    "mushroom": "Mushroom",
    "custard apple": "Custard Apple",
    "fig": "Fig",
    "jackfruit": "Jackfruit",
}


class ProduceClassifier:
    """
    Real-world vision classifier supporting:
    1. Real-world camera captures (natural backgrounds, lighting, hands).
    2. 26 core supermarket produce classes.
    3. Dynamic new product onboarding and prototype learning.
    4. General object detection from 1,000 real-world classes.
    """
    def __init__(
        self,
        model_path: str = None,
        config_path: str = None,
        prototypes_path: str = None
    ):
        self.device = torch.device("cpu")
        self.weights = models.MobileNet_V3_Small_Weights.DEFAULT
        self.model = models.mobilenet_v3_small(weights=self.weights).eval().to(self.device)
        self.transform = self.weights.transforms()
        self.categories = self.weights.meta["categories"]

        self.prototypes_path = prototypes_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "artifacts", "prototypes.json"
        )
        self.prototypes = {}
        self.load_prototypes()

    def load_prototypes(self):
        """Loads registered product prototypes."""
        if os.path.exists(self.prototypes_path):
            try:
                with open(self.prototypes_path, "r") as f:
                    self.prototypes = json.load(f)
            except Exception as e:
                print(f"Error loading prototypes: {e}")
                self.prototypes = {}

    def save_prototypes(self):
        """Persists registered product prototypes."""
        os.makedirs(os.path.dirname(self.prototypes_path), exist_ok=True)
        with open(self.prototypes_path, "w") as f:
            json.dump(self.prototypes, f)

    def extract_embedding(self, image: Image.Image) -> np.ndarray:
        """Extracts normalized 576-dimensional semantic feature vector."""
        img_tensor = self.transform(image.convert("RGB")).unsqueeze(0).to(self.device)
        with torch.no_grad():
            feat = self.model.avgpool(self.model.features(img_tensor)).flatten(1)
            feat = feat / torch.norm(feat, dim=1, keepdim=True)
            return feat.cpu().numpy()[0]

    def register_product(self, visual_class: str, image: Optional[Image.Image] = None, embedding: Optional[List[float]] = None):
        """
        Dynamically enrolls a new product prototype into the classifier.
        Allows the system to immediately recognize this new product on subsequent scans!
        """
        if embedding is None and image is not None:
            embedding = self.extract_embedding(image).tolist()
        if embedding is not None:
            self.prototypes[visual_class] = embedding
            self.save_prototypes()

    def predict(self, image: Image.Image, top_k: int = 3) -> Dict[str, Any]:
        """
        Runs real-world inference on input image:
        - Evaluates cosine similarities against all registered catalog prototypes.
        - Evaluates generic ImageNet top-3 predictions.
        - Returns ranked candidates, decision action, and new product detection status.
        """
        rgb_img = image.convert("RGB")
        img_tensor = self.transform(rgb_img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            # 1. Feature embedding
            feat = self.model.avgpool(self.model.features(img_tensor)).flatten(1)
            feat = feat / torch.norm(feat, dim=1, keepdim=True)
            feat_np = feat.cpu().numpy()[0]

            # 2. General classification logits
            logits = self.model.classifier(feat)
            probs = torch.softmax(logits, dim=-1)[0]
            top_imagenet_indices = torch.topk(probs, 3).indices.tolist()

        imagenet_top_label = self.categories[top_imagenet_indices[0]]
        imagenet_top_conf = float(probs[top_imagenet_indices[0]].item())

        # 3. Compute cosine similarity against all registered catalog prototypes
        sim_scores = []
        for v_class, proto_vec in self.prototypes.items():
            proto_arr = np.array(proto_vec, dtype=np.float32)
            cosine_sim = float(np.dot(feat_np, proto_arr))
            sim_scores.append((v_class, cosine_sim))

        # Sort by similarity descending
        sim_scores.sort(key=lambda x: x[1], reverse=True)

        candidates = []
        seen_classes = set()

        # Check if top ImageNet label directly maps to a known produce class
        mapped_produce = IMAGENET_TO_PRODUCE_MAP.get(imagenet_top_label.lower()) or IMAGENET_TO_PRODUCE_MAP.get(imagenet_top_label)

        if mapped_produce and mapped_produce in self.prototypes and imagenet_top_conf > 0.40:
            candidates.append({
                "visual_class": mapped_produce,
                "confidence": round(min(0.99, max(0.85, imagenet_top_conf)), 4),
                "is_new_product": False
            })
            seen_classes.add(mapped_produce)

        for v_class, sim in sim_scores:
            if v_class in seen_classes:
                continue
            # Convert cosine similarity (typically 0.3 - 0.9) to calibrated probability
            calibrated_prob = max(0.01, min(0.99, (sim - 0.20) / 0.70))
            candidates.append({
                "visual_class": v_class,
                "confidence": round(calibrated_prob, 4),
                "is_new_product": False
            })
            seen_classes.add(v_class)
            if len(candidates) >= top_k:
                break

        # Check if the scanned item is a completely NEW or UNCATALOGED product
        top_cand_conf = candidates[0]["confidence"] if candidates else 0.0
        top_cand_name = candidates[0]["visual_class"] if candidates else "Unknown"

        is_new_product = False
        # If top similarity is below 0.50 OR if ImageNet strongly predicts an uncataloged object
        if top_cand_conf < 0.50 or (mapped_produce is None and imagenet_top_conf > 0.45 and imagenet_top_label not in [c["visual_class"].lower() for c in candidates]):
            is_new_product = True
            # Prepend the new detected product candidate
            suggested_title = imagenet_top_label.replace("_", " ").title()
            candidates.insert(0, {
                "visual_class": f"New Product ({suggested_title})",
                "suggested_name": suggested_title,
                "confidence": round(imagenet_top_conf if imagenet_top_conf > 0.5 else 0.75, 4),
                "is_new_product": True
            })
            if len(candidates) > top_k:
                candidates = candidates[:top_k]

        top_confidence = candidates[0]["confidence"]

        # Decision Policy Matrix
        if candidates[0].get("is_new_product"):
            status = "new_product_detected"
            decision = {
                "action": "verify_new_product",
                "reason": f"New or uncataloged product detected ('{candidates[0].get('suggested_name', 'New Item')}'). Please verify details to add to catalog and basket."
            }
        elif top_confidence >= 0.75:
            status = "high_confidence"
            decision = {
                "action": "confirm_top_candidate",
                "reason": f"High confidence match ('{candidates[0]['visual_class']}'). Please confirm."
            }
        elif top_confidence >= 0.45:
            status = "medium_confidence"
            decision = {
                "action": "select_from_top_k",
                "reason": "Medium confidence match. Please choose from suggested choices."
            }
        else:
            status = "low_confidence"
            decision = {
                "action": "verify_new_product",
                "reason": "Unrecognized item. You can register it as a new product or search catalog."
            }

        return {
            "status": status,
            "top_confidence": round(top_confidence, 4),
            "candidates": candidates,
            "decision": decision,
            "open_set_distance": round(1.0 - top_confidence, 2),
            "is_unknown": is_new_product,
            "feature_vector": feat_np.tolist()
        }
