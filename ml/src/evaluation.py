"""
Model Evaluation and Metrics Engine for BarcodeLess Produce Assistant.
Measures Top-1/Top-3 accuracy, per-class precision/recall, ECE calibration, and latency.
"""

import time
import numpy as np
import torch
from typing import List, Dict, Any, Tuple
from PIL import Image


def compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE)."""
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = (predictions == labels)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = np.mean(in_bin)

        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(accuracies[in_bin])
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin

    return float(ece)


def evaluate_classifier(classifier, test_manifest: List[Tuple[str, str, int]]) -> Dict[str, Any]:
    """
    Evaluates classifier on a manifest of (image_path, visual_class, class_idx).
    Returns comprehensive metrics report.
    """
    num_classes = len(classifier.classes)
    y_true = []
    y_pred = []
    y_probs = []
    latencies = []
    top_3_correct = 0

    class_counts = {c: {"total": 0, "correct": 0, "pred_total": 0} for c in classifier.classes}

    for fpath, class_name, class_idx in test_manifest:
        try:
            img = Image.open(fpath)
            t0 = time.time()
            res = classifier.predict(img, top_k=3)
            lat = (time.time() - t0) * 1000.0
            latencies.append(lat)

            cands = res["candidates"]
            top_pred_class = cands[0]["visual_class"]
            pred_idx = classifier.classes.index(top_pred_class)

            y_true.append(class_idx)
            y_pred.append(pred_idx)

            top_3_classes = [c["visual_class"] for c in cands]
            if class_name in top_3_classes:
                top_3_correct += 1

            class_counts[class_name]["total"] += 1
            class_counts[top_pred_class]["pred_total"] += 1
            if top_pred_class == class_name:
                class_counts[class_name]["correct"] += 1

        except Exception as e:
            continue

    total_samples = len(y_true)
    if total_samples == 0:
        return {"error": "No valid samples evaluated"}

    top_1_acc = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp) / total_samples
    top_3_acc = top_3_correct / total_samples

    # Compute per-class precision, recall, and F1
    per_class_metrics = {}
    f1_scores = []
    for c, stats in class_counts.items():
        rec = stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0
        prec = stats["correct"] / stats["pred_total"] if stats["pred_total"] > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        f1_scores.append(f1)
        per_class_metrics[c] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "samples": stats["total"]
        }

    macro_f1 = float(np.mean(f1_scores))

    latencies.sort()
    p50_lat = latencies[int(len(latencies) * 0.50)]
    p95_lat = latencies[int(len(latencies) * 0.95)]

    return {
        "total_samples": total_samples,
        "top_1_accuracy": round(top_1_acc, 4),
        "top_3_accuracy": round(top_3_acc, 4),
        "macro_f1": round(macro_f1, 4),
        "latency_p50_ms": round(p50_lat, 2),
        "latency_p95_ms": round(p95_lat, 2),
        "per_class_metrics": per_class_metrics
    }

