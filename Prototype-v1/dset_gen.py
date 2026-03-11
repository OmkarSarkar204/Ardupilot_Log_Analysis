# import json
# import csv

# INPUT_FILE = "feat.json"
# OUTPUT_FILE = "dataset.csv"

# SPREAD_THRESHOLD = 400
# PWM_THRESHOLD = 1800

# with open(INPUT_FILE, "r") as f:
#     data = json.load(f)

# features = data["feature_vectors"]

# with open(OUTPUT_FILE, "w", newline="") as csvfile:
#     writer = csv.writer(csvfile)

#     writer.writerow(["time_sec", "motor_spread", "max_pwm", "roll_error", "label"])

#     for entry in features:
#         time_sec = entry["time_sec"]
#         spread = entry["motor_spread"]
#         max_pwm = entry["max_pwm"]
#         roll_error = entry["roll_error"]

#         if spread > SPREAD_THRESHOLD and max_pwm > PWM_THRESHOLD:
#             label = 1
#         else:
#             label = 0

#         writer.writerow([time_sec, spread, max_pwm, roll_error, label])

# print("dataset.csv generated")

import pandas as pd

df = pd.read_csv("dataset.csv")

print("total rows:", len(df))
print("anomalies:", df["label"].sum())
print("ratio:", df["label"].sum() / len(df))