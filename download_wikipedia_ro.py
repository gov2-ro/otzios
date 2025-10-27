#!/usr/bin/env python3
"""
Download Romanian Wikipedia dataset using HuggingFace datasets.

This script downloads the Wikipedia Romanian dataset to HuggingFace cache.
The dataset will be used for corpus validation of forgotten words.

Dataset info:
- Language: Romanian (ro)
- Size: ~1.2-1.5 GB
- Articles: ~500k
- Source: Wikimedia dumps via HuggingFace
"""

import sys
from datasets import load_dataset

def download_wikipedia_romanian():
    """Download Wikipedia Romanian dataset."""

    print("=" * 70)
    print("Wikipedia Romanian Dataset Downloader")
    print("=" * 70)
    print()

    print("This will download the Romanian Wikipedia dataset.")
    print("Size: ~1.2-1.5 GB")
    print("Storage location: ~/.cache/huggingface/datasets/")
    print()

    # Ask for confirmation
    response = input("Continue? [y/N]: ").strip().lower()
    if response not in ('y', 'yes'):
        print("Download cancelled.")
        sys.exit(0)

    print()
    print("Downloading Wikipedia Romanian dataset...")
    print("This may take 5-15 minutes depending on your connection.")
    print()

    try:
        # Load the dataset (will download and cache)
        dataset = load_dataset(
            "wikipedia",
            "20220301.ro",  # Romanian Wikipedia from March 2022
            split="train"
        )

        print()
        print("✅ Download complete!")
        print()
        print(f"Dataset info:")
        print(f"  - Articles: {len(dataset):,}")
        print(f"  - Columns: {dataset.column_names}")
        print(f"  - Cache location: ~/.cache/huggingface/datasets/")
        print()

        # Show sample
        print("Sample article:")
        print("-" * 70)
        sample = dataset[0]
        print(f"Title: {sample['title']}")
        print(f"Text preview: {sample['text'][:200]}...")
        print()

        print("Next steps:")
        print("  1. Run: python process_corpus.py --test")
        print("  2. Verify processing works")
        print("  3. Run: python process_corpus.py --full")
        print()

    except Exception as e:
        print()
        print(f"❌ Error downloading dataset: {e}")
        print()
        print("Troubleshooting:")
        print("  - Check internet connection")
        print("  - Ensure ~2 GB free space in ~/.cache/")
        print("  - Try again later if HuggingFace is down")
        sys.exit(1)

if __name__ == "__main__":
    download_wikipedia_romanian()
