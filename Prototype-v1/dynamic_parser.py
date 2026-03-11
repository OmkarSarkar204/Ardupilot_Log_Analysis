import json
from pymavlink import mavutil

log_file = "00000082.BIN"

log = mavutil.mavlink_connection(log_file)

parameters = {}
motor_channels = set()

att_signals = []
rcou_signals = []

message_count = 0


while True:
    msg = log.recv_match(type=["ATT", "RCOU", "PARM"], blocking=False)

    if msg is None:
        break

    message_count += 1

    data = msg.to_dict()
    mtype = msg.get_type()

    if mtype == "PARM":

        name = data.get("Name")
        value = data.get("Value")

        if name is None or value is None:
            continue

        parameters[name] = value

        # Detect motor channels
        if name.startswith("SERVO") and name.endswith("_FUNCTION"):

            if 33 <= value <= 44:

                ch = int(name.replace("SERVO", "").replace("_FUNCTION", ""))
                motor_channels.add(ch)

        continue

    if mtype == "ATT":

        time = data.get("TimeUS")
        roll = data.get("Roll")
        des_roll = data.get("DesRoll")

        if time is None:
            continue

        att_signals.append({
            "time_us": time,
            "roll": roll,
            "des_roll": des_roll
        })

    if mtype == "RCOU":

        time = data.get("TimeUS")

        if time is None:
            continue

        motor_outputs = {}

        for ch in motor_channels:

            val = data.get(f"C{ch}")

            if val is not None:
                motor_outputs[f"C{ch}"] = val

        if motor_outputs:

            rcou_signals.append({
                "time_us": time,
                "outputs": motor_outputs
            })

parsed_log = {
    "log_file": log_file,
    "messages_parsed": message_count,
    "motor_channels": sorted(list(motor_channels)),
    "parameters": parameters,
    "signals": {
        "ATT": att_signals,
        "RCOU": rcou_signals
    }
}
with open("signals.json", "w") as f:
    json.dump(parsed_log, f, indent=4)

print("Parsing complete.")
print("Signals saved to signals.json")