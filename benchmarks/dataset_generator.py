#!/usr/bin/env python3
"""Generate test datasets."""
import numpy as np
from PIL import Image
import os

def generate_dataset(output_dir, count=100, size=(512, 512)):
    os.makedirs(output_dir, exist_ok=True)
    for i in range(count):
        arr = np.random.randint(0, 256, (*size, 3), dtype=np.uint8)
        Image.fromarray(arr).save(os.path.join(output_dir, f"img_{i:04d}.png"))

if __name__ == "__main__":
    generate_dataset("./dataset")
