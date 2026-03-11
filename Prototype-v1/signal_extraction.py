import bisect
from pymavlink import mavutil

log = mavutil.mavlink_connection("00000082.BIN")

att_time = []
att_error = []

rcou_time = []
rcou_spread = []
rcou_max_pwm = []

servo_max_values = []

while True:
    msg = log.recv_match(type=["ATT","RCOU","PARM"], blocking=False)
    if msg is None:
        break

    data = msg.to_dict()
    mtype = msg.get_type()

    if mtype == "PARM":
        name = data.get("Name")
        value = data.get("Value")

        if name in ["SERVO1_MAX","SERVO2_MAX","SERVO3_MAX","SERVO4_MAX"]:
            servo_max_values.append(value)
        continue

    time = data.get("TimeUS")
    if time is None:
        continue

    if mtype == "ATT":
        roll = data.get("Roll")
        des_roll = data.get("DesRoll")

        if roll is not None and des_roll is not None:
            att_time.append(time)
            att_error.append(abs(des_roll - roll))

    if mtype == "RCOU":
        motors = [data.get("C1"),data.get("C2"),data.get("C3"),data.get("C4")]

        if None not in motors:
            rcou_time.append(time)
            rcou_spread.append(max(motors)-min(motors))
            rcou_max_pwm.append(max(motors))


# determine PWM ceiling dynamically
if servo_max_values:
    pwm_max = max(servo_max_values)
else:
    pwm_max = max(rcou_max_pwm)

print("PWM ceiling:", pwm_max)

MOTOR_SPREAD_THRESHOLD = 300

for i,spread in enumerate(rcou_spread):

    max_pwm = rcou_max_pwm[i]

    if spread > MOTOR_SPREAD_THRESHOLD:

        target_time = rcou_time[i]

        pos = bisect.bisect_left(att_time,target_time)

        if pos == 0:
            closest = 0
        elif pos == len(att_time):
            closest = len(att_time)-1
        else:
            before = att_time[pos-1]
            after = att_time[pos]

            if abs(before-target_time) <= abs(after-target_time):
                closest = pos-1
            else:
                closest = pos

        roll_err = att_error[closest]

        print("\nMotor Imbalance Event")
        print("Time:",target_time/1_000_000)
        print("Spread:",spread)
        print("PWM:",max_pwm)
        print("Roll Error:",roll_err)
        
        break
 