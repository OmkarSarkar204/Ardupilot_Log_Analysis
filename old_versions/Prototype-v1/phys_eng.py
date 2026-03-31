import json
import pandas as pd

INP_FILE = "signals.json"
OUTP_FILE = "feat.json"

MOTOR_SPREAD_THRESHOLD = 300  # hardcoded for now will learn better later from dataset
GROUND_PWM_LIMIT = 1200       # below this drone mostly on ground or motors are idle

with open(INP_FILE, "r") as f:
  data = json.load(f)

att_signals = data["signals"]["ATT"]
rcou_signals = data["signals"]["RCOU"]

motor_channels = data["motor_channels"]


# rebuilding the ATT arrays again easier for time sync later
att_df = pd.DataFrame(att_signals)

att_df = att_df.rename(columns={
  "time_us": "time",
  "roll": "roll",
  "des_roll": "des_roll"
})

att_df = att_df.dropna(subset=["time", "roll", "des_roll"])

# simple roll error calc
att_df["roll_error"] = (att_df["des_roll"] - att_df["roll"]).abs()

att_df = att_df.sort_values("time")


rows = []

# loop through motor outputs timeline
for rcou in rcou_signals:

  time = rcou["time_us"]
  outputs = rcou["outputs"]

  motors = []

  # collect pwm of motors only
  for ch in motor_channels:
    key = f"C{ch}"

    if key in outputs:
      motors.append(outputs[key])

  # if some motor packet missing or broken so skip
  if len(motors) != len(motor_channels):
    continue

  spread = max(motors) - min(motors)
  max_pwm = max(motors)

  rows.append({
    "time": time,
    "motor_spread": spread,
    "max_pwm": max_pwm
  })


rcou_df = pd.DataFrame(rows)

rcou_df = rcou_df.sort_values("time")


# align ATT and motor data based on closest time
df = pd.merge_asof(
  rcou_df,
  att_df[["time", "roll_error"]],
  on="time",
  direction="nearest"
)


# filter out idle / ground state data
df = df[df["max_pwm"] > GROUND_PWM_LIMIT]


df["time_sec"] = df["time"] / 1_000_000


feature_vectors = df[[
  "time_sec",
  "motor_spread",
  "max_pwm",
  "roll_error"
]].to_dict(orient="records")


features = {
  "log_file": data["log_file"],
  "motor_channels": motor_channels,
  "feature_vectors": feature_vectors
}


with open(OUTP_FILE, "w") as f:
  json.dump(features, f, indent=2)


print("feature extraction done saved to feat.json")