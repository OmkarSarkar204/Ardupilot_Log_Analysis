import bisect
from pymavlink import mavutil

log = mavutil.mavlink_connection("00000082.BIN")

att_data = {"time": [], "error": []}
rcou_data = {"time": [], "spread": [], "max_pwm": []}
servo_max_values = []

message_counter = 0

while True:
    msg = log.recv_match(type=["ATT", "RCOU", "PARM"], blocking=False)

    if msg is None:
        break

    message_counter += 1

    data = msg.to_dict()
    msg_type = msg.get_type()

    # --- PARAMETER PARSING ---
    if msg_type == "PARM":
        name = data.get("Name")
        value = data.get("Value")

        if name in ["SERVO1_MAX", "SERVO2_MAX", "SERVO3_MAX", "SERVO4_MAX"]:
            servo_max_values.append(value)

        continue

    current_time = data.get("TimeUS")

    if current_time is None:
        continue

    # --- ATTITUDE DATA ---
    if msg_type == "ATT":

        des_roll = data.get("DesRoll")
        roll = data.get("Roll")

        if des_roll is not None and roll is not None:

            roll_error = abs(des_roll - roll)

            att_data["time"].append(current_time)
            att_data["error"].append(roll_error)

    # --- MOTOR OUTPUT DATA ---
    elif msg_type == "RCOU":

        motors = [
            data.get("C1"),
            data.get("C2"),
            data.get("C3"),
            data.get("C4")
        ]

        if None not in motors:

            spread = max(motors) - min(motors)
            max_pwm = max(motors)

            rcou_data["time"].append(current_time)
            rcou_data["spread"].append(spread)
            rcou_data["max_pwm"].append(max_pwm)


# --- PWM CEILING DETECTION ---
if servo_max_values:
    pwm_max = max(servo_max_values)
else:
    pwm_max = 2000

print("\n---- DEBUG INFO ----")
print("Messages parsed:", message_counter)
print("ATT samples:", len(att_data["time"]))
print("RCOU samples:", len(rcou_data["time"]))

print("PWM ceiling:", pwm_max)

# --- SIGNAL SUMMARY ---
if rcou_data["spread"]:
    print("\nSignal Summary")
    print("Max motor spread:", max(rcou_data["spread"]))
    print("Max PWM:", max(rcou_data["max_pwm"]))

if att_data["error"]:
    print("Max roll error:", max(att_data["error"]))


# --- SIMPLE MOTOR IMBALANCE CHECK ---
MOTOR_SPREAD_THRESHOLD = 300
RUNNING_PWM_THRESHOLD = 1200

print("\n---- Event Scan ----")

for i, spread in enumerate(rcou_data["spread"]):

    max_pwm = rcou_data["max_pwm"][i]

    if spread > MOTOR_SPREAD_THRESHOLD and max_pwm > RUNNING_PWM_THRESHOLD:

        event_time = rcou_data["time"][i]

        idx = bisect.bisect_left(att_data["time"], event_time)

        if idx == 0:
            closest_idx = 0
        elif idx == len(att_data["time"]):
            closest_idx = len(att_data["time"]) - 1
        else:
            before = att_data["time"][idx - 1]
            after = att_data["time"][idx]

            if abs(before - event_time) <= abs(after - event_time):
                closest_idx = idx - 1
            else:
                closest_idx = idx

        roll_error = att_data["error"][closest_idx]

        print("\nMotor Imbalance Event")
        print("Time:", event_time / 1_000_000)
        print("Spread:", spread)
        print("PWM:", max_pwm)
        print("Roll Error:", roll_error)