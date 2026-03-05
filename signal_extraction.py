from pymavlink import mavutil

log = mavutil.mavlink_connection("00000049.BIN")

att_data = {"time": [], "error": []}
rcou_data = {"time": [], "spread": [], "max_pwm": []}
bat_data = {"time": [], "voltage": []}
vibe_data = {"time": [], "max_vibe": []}

servo_max_values = []

while True:
    scrp = log.recv_match(type=["ATT", "RCOU", "BAT", "VIBE", "PARM"], blocking=False)
    
    if scrp is None:
        break

    data = scrp.to_dict()
    scrp_type = scrp.get_type()

    if scrp_type == "PARM":
        name = data.get("Name")
        value = data.get("Value")

        if name in ["SERVO1_MAX", "SERVO2_MAX", "SERVO3_MAX", "SERVO4_MAX"]:
            servo_max_values.append(value)
        continue

    current_time = data.get("TimeUS")

    if current_time is None:
        continue

    if scrp_type == "ATT":
        des_roll = data.get("DesRoll")
        roll = data.get("Roll")

        if des_roll is not None and roll is not None:
            att_data["time"].append(current_time)
            att_data["error"].append(abs(des_roll - roll))

    elif scrp_type == "RCOU":
        motors = [data.get("C1"), data.get("C2"), data.get("C3"), data.get("C4")]

        if None not in motors:
            rcou_data["time"].append(current_time)
            rcou_data["spread"].append(max(motors) - min(motors))
            rcou_data["max_pwm"].append(max(motors))

    elif scrp_type == "BAT":
        voltage = data.get("Volt")

        if voltage is not None:
            bat_data["time"].append(current_time)
            bat_data["voltage"].append(voltage)

    elif scrp_type == "VIBE":
        vx, vy, vz = data.get("VibeX"), data.get("VibeY"), data.get("VibeZ")

        if None not in (vx, vy, vz):
            vibe_data["time"].append(current_time)
            vibe_data["max_vibe"].append(max(vx, vy, vz))

if servo_max_values:
    pwm_max = max(servo_max_values)
else:
    pwm_max = 2000 

PWM_SATURATION_LIMIT = 0.95 * pwm_max

print("Detected PWM ceiling:", pwm_max)
print("Dynamic PWM limit:", PWM_SATURATION_LIMIT)

print(f"ATT samples: {len(att_data['error'])}")
print(f"Motor samples: {len(rcou_data['spread'])}")
print(f"Battery samples: {len(bat_data['voltage'])}")
print(f"Vibration samples: {len(vibe_data['max_vibe'])}")

MOTOR_SPREAD_THRESHOLD = 300
REQUIRED_SUSTAINED_SAMPLES = 5

consecutive_spikes = 0

print("Max spread observed:", max(rcou_data["spread"]))
print("Max PWM observed:", max(rcou_data["max_pwm"]))

for i, spread in enumerate(rcou_data["spread"]):
    max_pwm = rcou_data["max_pwm"][i]

    if spread > MOTOR_SPREAD_THRESHOLD and max_pwm > PWM_SATURATION_LIMIT:
        consecutive_spikes += 1

        if consecutive_spikes >= REQUIRED_SUSTAINED_SAMPLES:
            t = rcou_data["time"][i] / 1_000_000

            print("\nMotor Imbalance Detected")
            print(f"Time: {t:.2f} s")
            print(f"Sustained Spread: {spread}")
            print(f"Max PWM: {max_pwm}")

            break
    else:
        consecutive_spikes = 0

else:
    print("No motor imbalance detected.")