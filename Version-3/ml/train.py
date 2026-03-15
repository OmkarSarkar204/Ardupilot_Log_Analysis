import os
import pandas as pd
from src.parser.parser import parse_log
from src.engines.phy_engine import process_physics
from ml_analyser import TelemetryMLAnalyzer


def compile_dataset(dataset_dir):
    training_dataframes = []
    log_files = []

    for f in os.listdir(dataset_dir):
        if f.lower().endswith(".bin"):
            log_files.append(os.path.join(dataset_dir, f))

    for file_path in log_files:

        filename = os.path.basename(file_path).lower()

        if "healthy" in filename:
            label = 0
            category = "HEALTHY"

        elif "motor_fail" in filename:
            label = 1
            category = "MOTOR_FAIL"

        elif "batt_fail" in filename or "battery" in filename:
            label = 2
            category = "BATTERY_FAIL"

        else:
            continue

        print("processing", category, filename)

        raw_data = parse_log(file_path)
        df = process_physics(raw_data, label=label)

        if df.empty:
            print("skip file maybe bad log", filename)
            continue

        if "Volt" in df.columns:
            df = df[df["Volt"] > 5.0].copy()

        ## crash logs contain healthy section in beginning
        if label > 0:
            crash_index = int(len(df) * 0.70)
            df.iloc[:crash_index, df.columns.get_loc("label")] = 0

        training_dataframes.append(df)

    return training_dataframes


if __name__ == "__main__":

    dfs = compile_dataset("dataset")

    if not dfs:
        print("Check if 'dataset/' contains .BIN files.")
        exit()

    master_df = pd.concat(dfs, ignore_index=True)
    master_df.to_csv("fdir_training_dataset.csv", index=False)
    print("Dataset saved to 'fdir_training_dataset.csv'.")

    os.makedirs("models", exist_ok=True)

    analyzer = TelemetryMLAnalyzer()
    analyzer.train(dfs)
    analyzer.save_model("models/telemetry_rf_model.pkl")

    print("Model saved")