from pymavlink import mavutil

def parse_log(log_file):
    log = mavutil.mavlink_connection(log_file)
    
    TARGET_MESSAGES = ["ATT", "BAT", "VIBE"]
    signals_dict = {msg: [] for msg in TARGET_MESSAGES}
    
    parameters = {}
    motor_channels = set()
    rcou_signals = []
    message_count = 0
    
    all_message_types = TARGET_MESSAGES + ["PARM", "RCOU"]
    
    while True:
        msg = log.recv_match(type=all_message_types, blocking=False)
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
            
            if name.startswith("SERVO") and name.endswith("_FUNCTION"):
                # ArduPilot spec: Motors 1-8 (33-40) and Motors 9-12 (82-85)
                if (33 <= value <= 40) or (82 <= value <= 85):
                    ch = int(name.replace("SERVO", "").replace("_FUNCTION", ""))
                    motor_channels.add(ch)
            continue
            
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
            continue
            
        if mtype in TARGET_MESSAGES:
            signals_dict[mtype].append(data)

    parsed_log = {
        "log_file": log_file,
        "messages_parsed": message_count,
        "motor_channels": sorted(list(motor_channels)),
        "parameters": parameters,
        "signals": {
            **signals_dict,
            "RCOU": rcou_signals
        }
    }
    
    return parsed_log