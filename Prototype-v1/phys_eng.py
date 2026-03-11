import json
import bisect

INP_FILE = "signals.json"
OUTP_FILE = "feat.json"

MOTOR_SPREAD_THRESHOLD = 300  # hardcoded for now will learn better later from dataset
GROUND_PWM_LIMIT = 1200       # below this drone mostly on ground or motors are idle

with open(INP_FILE, "r") as f:
  data = json.load(f)

att_signals = data["signals"]["ATT"]
rcou_signals = data["signals"]["RCOU"]

motor_channels = data["motor_channels"]

att_time = []
att_roll = []
att_des_roll = []

# rebuilding the ATT arrays again easier for bisect search later
for entry in att_signals:
  t = entry["time_us"]
  roll = entry["roll"]
  des_roll = entry["des_roll"]

  if t is None or roll is None or des_roll is None:
    continue

  att_time.append(t)
  att_roll.append(roll)
  att_des_roll.append(des_roll)

# simple roll error calc
att_error = [abs(d - r) for d, r in zip(att_des_roll, att_roll)]

feature_vectors = []

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

  # filter out idle / ground state data
  if max_pwm <= GROUND_PWM_LIMIT:
    continue

  # find nearest ATT sample for same moment
  pos = bisect.bisect_left(att_time, time)

  if pos == 0:
    closest = 0
  elif pos == len(att_time):
    closest = len(att_time) - 1
  else:
    before = att_time[pos - 1]
    after = att_time[pos]

    if abs(before - time) <= abs(after - time):
      closest = pos - 1
    else:
      closest = pos

  roll_error = att_error[closest]

  # store vector for later ML stage
  feature_vectors.append({
    "time_sec": time / 1_000_000,
    "motor_spread": spread,
    "max_pwm": max_pwm,
    "roll_error": roll_error
  })

features = {
  "log_file": data["log_file"],
  "motor_channels": motor_channels,
  "feature_vectors": feature_vectors
}

with open(OUTP_FILE, "w") as f:
  json.dump(features, f, indent=2)

print("feature extraction done saved to feat.json")