"""
Training pipeline for BarcodeLess Produce Assistant ProduceNet.
Trains on supermarket produce classes from Fruits-360, computes prototypes, evaluates on test set,
and exports artifacts with validation metrics.
"""

import os
import json
import hashlib
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import torchvision.transforms as transforms

from ml.src.data import PILOT_CLASS_MAP, load_dataset_manifest
from ml.src.classifier import ProduceNet, ProduceClassifier
from ml.src.evaluation import evaluate_classifier
from services.database import get_db, init_db


class FruitsDataset(Dataset):
    def __init__(self, manifest, transform=None):
        self.manifest = manifest
        self.transform = transform

    def __len__(self):
        return len(self.manifest)

    def __getitem__(self, idx):
        path, class_name, class_idx = self.manifest[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, class_idx


def main():
    print("=== BarcodeLess Produce Assistant: Model Training & Evaluation ===")
    classes = sorted(list(PILOT_CLASS_MAP.keys()))
    num_classes = len(classes)
    print(f"Target classes ({num_classes}): {classes[:8]} ...")

    # Load manifests
    train_manifest = load_dataset_manifest("fruits-360", split="Training", max_per_class=120)
    test_manifest = load_dataset_manifest("fruits-360", split="Test", max_per_class=40)
    print(f"Loaded {len(train_manifest)} training images and {len(test_manifest)} test images.")

    # Transforms with data augmentation for training
    train_transform = transforms.Compose([
        transforms.Resize((64, 64)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    test_transform = transforms.Compose([
        transforms.Resize((64, 64)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_dataset = FruitsDataset(train_manifest, transform=train_transform)
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True, num_workers=2)

    device = torch.device("cpu")
    model = ProduceNet(num_classes=num_classes).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    # Train for 4 epochs
    print("\nTraining ProduceNet...")
    epochs = 4
    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        t0 = time.time()

        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            logits, _ = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            preds = torch.argmax(logits, dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

        epoch_loss = running_loss / total
        epoch_acc = correct / total
        elapsed = time.time() - t0
        print(f"Epoch [{epoch+1}/{epochs}] - Loss: {epoch_loss:.4f} - Accuracy: {epoch_acc*100:.2f}% ({elapsed:.1f}s)")

    # Compute prototype embeddings per class
    print("\nExtracting feature prototypes for open-set rejection...")
    model.eval()
    prototypes = {i: [] for i in range(num_classes)}
    feature_loader = DataLoader(FruitsDataset(train_manifest, transform=test_transform), batch_size=64, shuffle=False)

    with torch.no_grad():
        for images, labels in feature_loader:
            images = images.to(device)
            features = model.extract_features(images)
            features_np = features.cpu().numpy()
            labels_np = labels.numpy()
            for feat, lbl in zip(features_np, labels_np):
                prototypes[lbl].append(feat)

    proto_matrix = np.zeros((num_classes, 128), dtype=np.float32)
    for i in range(num_classes):
        if len(prototypes[i]) > 0:
            proto_matrix[i] = np.mean(prototypes[i], axis=0)

    # Save artifacts
    artifacts_dir = "ml/artifacts"
    os.makedirs(artifacts_dir, exist_ok=True)
    model_path = os.path.join(artifacts_dir, "produce_net_v1.pth")
    config_path = os.path.join(artifacts_dir, "config.json")

    torch.save({
        "num_classes": num_classes,
        "classes": classes,
        "model_state_dict": model.state_dict(),
        "prototypes": proto_matrix.tolist()
    }, model_path)

    config_data = {
        "model_name": "produce-classifier",
        "version": "1.0.0",
        "num_classes": num_classes,
        "classes": classes,
        "temperature": 1.15,
        "open_set_threshold": 8.5,
        "prototypes": proto_matrix.tolist()
    }
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=2)

    # Compute checksum
    hasher = hashlib.sha256()
    with open(model_path, "rb") as f:
        hasher.update(f.read())
    model_checksum = hasher.hexdigest()

    print(f"\nSaved model weights to {model_path} (SHA-256: {model_checksum[:12]}...)")

    # Evaluate on test set
    print("\nEvaluating model on test dataset...")
    classifier = ProduceClassifier(model_path=model_path, config_path=config_path)
    eval_report = evaluate_classifier(classifier, test_manifest)

    print("\n=== Model Validation Report ===")
    print(f"Total Test Samples: {eval_report['total_samples']}")
    print(f"Top-1 Accuracy:     {eval_report['top_1_accuracy']*100:.2f}%")
    print(f"Top-3 Accuracy:     {eval_report['top_3_accuracy']*100:.2f}%")
    print(f"Macro F1 Score:     {eval_report['macro_f1']:.4f}")
    print(f"Latency p50:        {eval_report['latency_p50_ms']} ms")
    print(f"Latency p95:        {eval_report['latency_p95_ms']} ms")

    # Save report
    report_path = os.path.join(artifacts_dir, "evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(eval_report, f, indent=2)
    print(f"Saved evaluation report to {report_path}")

    # Register into database
    init_db()
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO model_versions 
            (id, name, version, artifact_uri, checksum, metrics_json, approval_status, deployed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            "MODEL-PRODUCE-1.0.0",
            "produce-classifier",
            "1.0.0",
            model_path,
            model_checksum,
            json.dumps({
                "top_1_accuracy": eval_report["top_1_accuracy"],
                "top_3_accuracy": eval_report["top_3_accuracy"],
                "macro_f1": eval_report["macro_f1"],
                "latency_p95_ms": eval_report["latency_p95_ms"]
            }),
            "approved"
        ))
    print("Registered model version 1.0.0 in model_versions registry.")


if __name__ == "__main__":
    main()

