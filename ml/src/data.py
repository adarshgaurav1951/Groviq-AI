"""
Dataset loader and preprocessor for BarcodeLess Produce Assistant.
Handles mapping from Fruits-360 raw directories to standardized supermarket produce classes.
"""

import os
from typing import Dict, List, Tuple
from PIL import Image

PILOT_CLASS_MAP = {
    "Apple Red Delicious": "Apple Red Delicious 1",
    "Apple Golden": "Apple Golden 1",
    "Apple Granny Smith": "Apple Granny Smith 1",
    "Banana": "Banana 1",
    "Orange": "Orange 1",
    "Lemon": "Lemon 1",
    "Limes": "Limes 1",
    "Tomato": "Tomato 1",
    "Potato": "Potato White 1",
    "Onion Red": "Onion Red 1",
    "Carrot": "Carrot 1",
    "Cucumber": "Cucumber 1",
    "Pear": "Pear 2",
    "Peach": "Peach 3",
    "Mango": "Mango 1",
    "Strawberry": "Strawberry 2",
    "Grape Blue": "Grape Blue 1",
    "Grape White": "Grape White 1",
    "Avocado": "Avocado 1",
    "Eggplant": "Eggplant long 1",
    "Pineapple": "Pineapple 1",
    "Kiwi": "Kiwi 2",
    "Pomegranate": "Pomegranate 1",
    "Watermelon": "Watermelon 1",
    "Pepper Green": "Pepper Green 1",
    "Pepper Red": "Pepper Red 5",
}


def get_dataset_paths(base_dir: str = "fruits-360") -> Tuple[str, str]:
    train_dir = os.path.join(base_dir, "Training")
    test_dir = os.path.join(base_dir, "Test")
    return train_dir, test_dir


def load_dataset_manifest(base_dir: str = "fruits-360", split: str = "Training", max_per_class: int = 150) -> List[Tuple[str, str, int]]:
    """
    Returns list of tuples: (image_path, visual_class, class_index)
    """
    split_dir = os.path.join(base_dir, split)
    classes = sorted(list(PILOT_CLASS_MAP.keys()))
    manifest = []

    for idx, visual_class in enumerate(classes):
        folder_name = PILOT_CLASS_MAP[visual_class]
        folder_path = os.path.join(split_dir, folder_name)
        if not os.path.exists(folder_path):
            continue
        filenames = sorted(os.listdir(folder_path))
        if max_per_class and max_per_class > 0:
            filenames = filenames[:max_per_class]
        for fname in filenames:
            if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                fpath = os.path.join(folder_path, fname)
                manifest.append((fpath, visual_class, idx))

    return manifest

