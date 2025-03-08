#!/usr/bin/env python3
"""Script to set up the data directories for Farsight2."""

import os
import sys

def setup_data_dirs():
    """Set up the data directories for Farsight2."""
    # Define the data directories
    data_dirs = [
        "data",
        "data/downloads",
        "data/processed",
        "data/embeddings",
        "data/test_suites",
        "data/evaluation_results"
    ]
    
    # Create the directories
    for directory in data_dirs:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    print("Data directories set up successfully.")

if __name__ == "__main__":
    setup_data_dirs() 