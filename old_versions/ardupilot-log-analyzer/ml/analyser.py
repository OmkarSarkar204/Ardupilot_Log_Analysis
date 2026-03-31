# analyser.py

import sys
import pandas as pd
import joblib
from src.parser.parser import parse_log
from src.engines.phy_eng import process_physics
from src.engines.phy_validator import physics_validator

def analyze_bin(bin_path):
    '''Vectorized pipeline with dynamic physical thresholds'''
    print(f"Analyzing log: {bin_path}\n")

    parsed_data = parse_log(bin_path)
    df = process_physics(parsed_data)
    df = df.reset_index(drop=True)

    model = joblib.load("models/drone_fault_model.pkl")

    features = ["motor_spread", "roll_error", "volt_sag", "power_watts"]
    X = df[features]
    df["ai_guess"] = model.predict(X)

    # Calculate dynamic thresholds using the first 20% of the log
    baseline = df.head(max(10, int(len(df) * 0.2)))
    spread_thresh = baseline["motor_spread"].mean() + (4 * baseline["motor_spread"].std())
    roll_thresh = baseline["roll_error"].mean() + (4 * baseline["roll_error"].std())
    sag_thresh = baseline["volt_sag"].mean() + (4 * baseline["volt_sag"].std())

    # Apply validator using the custom thresholds
    df["physics_check"] = df.apply(
        lambda row: physics_validator(
            row["motor_spread"],
            row["roll_error"],
            row["volt_sag"],
            row["power_watts"],
            spread_thresh,
            roll_thresh,
            sag_thresh
        ),
        axis=1
    )

    # Find where both engines agree
    motor_crashes = df[(df["ai_guess"] == 1) & (df["physics_check"] == 1)]
    batt_crashes = df[(df["ai_guess"] == 2) & (df["physics_check"] == 2)]

    if not motor_crashes.empty:
        start_time = motor_crashes["time_sec"].iloc[0]
        print("Decision: Motor Failure")
        print(f"Timestamp: {start_time:.2f} seconds\n")
    elif not batt_crashes.empty:
        start_time = batt_crashes["time_sec"].iloc[0]
        print("Decision: Battery Failure")
        print(f"Timestamp: {start_time:.2f} seconds\n")
    else:
        print("Decision: Healthy Flight")
        print("No confirmed anomalies detected.\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyser.py path/to/log.BIN")
        sys.exit(1)

    bin_file = sys.argv[1]
    analyze_bin(bin_file)