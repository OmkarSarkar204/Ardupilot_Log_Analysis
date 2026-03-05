import json
from pymavlink import mavutil

log = mavutil.mavlink_connection("00000049.BIN")

with open("motor_issue.json", "w") as f:
    while True:
        msg = log.recv_match(blocking=False)
        if msg is None:
            break
        
        data = msg.to_dict()
        json.dump(data, f)
        f.write("\n")