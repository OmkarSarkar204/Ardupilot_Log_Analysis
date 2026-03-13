import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.parser.parser import parse_log
from src.engines.phy_eng import process_physics


RAW_LOG_DIR = "data/raw_logs"
DATASET_PATH = "data/datasets/master_dataset.csv"

all_features = []

print("Starting batch dataset builder...\n")


for filename in os.listdir(RAW_LOG_DIR):

    if not filename.endswith(".BIN"):
        continue

    filepath = os.path.join(RAW_LOG_DIR, filename)

    name = filename.lower()

    # automatic labeling
    if "motor_fail" in name:
        label = 1
    elif "batt_fail" in name:
        label = 2
    else:
        label = 0

    print(f"Processing {filename}  label={label}")

    try:

        parsed = parse_log(filepath)

        df = process_physics(parsed, label=label)

        all_features.append(df)

    except Exception as e:
        print(f"FAILED: {filename}")
        print(e)
        print()


if all_features:

    print("\nBuilding master dataset...")

    dataset = pd.concat(all_features, ignore_index=True)

    dataset = dataset.dropna()

    dataset.to_csv(DATASET_PATH, index=False)

    print(f"\nDataset created at {DATASET_PATH}")
    print(f"Total rows: {len(dataset)}")

else:
    print("No logs processed.")