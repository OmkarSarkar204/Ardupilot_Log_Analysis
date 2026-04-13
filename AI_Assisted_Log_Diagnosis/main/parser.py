from pymavlink import mavutil
import json


class BinIngest:
    """Processing froward only Selected Targets for now"""
    def __init__(self, file_path):
        self.file_path = file_path
        self.connection = mavutil.mavlink_connection(file_path)

        self.schema = set()

        # RCOU: PWM output signals sent to motors
        # ESC: ESC including RPM
        # MOTB: Motor and battery interaction data
        # BAT: Battery voltage, current, and consumption
        # POWR: Flight controller power supply voltage and safety status
        # IMU: Combined accelerometer and gyroscope
        # VIBE: Processed vibration levels on X, Y, Z axes
        # ATT: Attitude data showing roll, pitch, yaw angles
        # XKF1: EKF state including attitude and velocity
        # ERR: Critical system error codes and failure flags

        self.targets = [
            "RCOU", "ESC", "MOTB",
            "BAT", "POWR", "IMU",
            "VIBE", "ATT", "XKF1",
            "ERR", "RPM", "PARM"
        ]

        self.data = {}

    # Ignoring errors sometimes generated while MAVLink Parsing
    def normalize_value(self, value):
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return value

    def reset(self):
        self.connection = mavutil.mavlink_connection(self.file_path)
    # 
    def parse(self):
        count = 0
        self.data = {}

        while True:
            message = self.connection.recv_match(blocking=False)
            if message is None:
                break
            
            count += 1
            msgtype = message.get_type()

            # Create containers
            if msgtype not in self.data:
                self.data[msgtype] = []

            # Store selected signals only for now
            if msgtype in self.targets:
                try:
                    # Convert MAVLink data into a dict
                    raw = message.to_dict()
                    clean = {}
                    for k, v in raw.items():
                        clean[k] = self.normalize_value(v)

                    self.data[msgtype].append(clean)
                except Exception:
                    continue
        self.active_signals = [k for k in self.targets if k in self.data]

        return count

    # microseconds to seconds
    @staticmethod
    def norm_time(data):
        for signal in data:
            for row in data[signal]:
                if "TimeUS" in row and row["TimeUS"] is not None:
                    row['TimeUS'] = row['TimeUS'] / 1e6

    def run(self):
        print("Parsing log")
        total = self.parse()
        return {
            "available_signals": self.active_signals,
            "total_messages": total,
            "data": self.data
        }

    def save(self, output_path, parsed_data):
        with open(output_path, "w") as f:
            json.dump(parsed_data, f, indent=2)


class MotorData:
    """Extracting motor related data"""
    def __init__(self, parm_data, rcou_data, esc_data=None, motb_data=None, bat_data=None, powr_data=None, rpm_data=None):
        self.parm_data = parm_data
        self.rcou_data = rcou_data
        self.esc_data = esc_data
        self.motb_data = motb_data
        self.bat_data = bat_data
        self.powr_data = powr_data
        self.rpm_data = rpm_data

        self.motor_map = {}
        self.valid = False

    # Mapping and assigning motors to its respective pins
    def build_mapping(self):
        self.motor_map = {}
        self.valid = False
        for p in self.parm_data:
            name = p.get("Name")
            value = p.get("Value")
            if value is None:
                continue

            if name and name.startswith("SERVO") and name.endswith("_FUNCTION"):
                try:
                    value = int(value)
                except:  # noqa: E722
                    continue
                servo_num = int(name[5:].split("_")[0])

                if 33 <= value <= 40:
                    motor_id = value - 32
                elif 82 <= value <= 85:
                    motor_id = value - 81 + 8
                else:
                    continue

                if f"Motor{motor_id}" not in self.motor_map:
                    self.motor_map[f"Motor{motor_id}"] = f"C{servo_num}"

        self.valid = len(self.motor_map) > 0
        return self.motor_map
    # Motor output values
    def get_motor_outputs(self):
        if not self.valid:
            return {}

        motor_outputs = {m: [] for m in self.motor_map}

        for row in self.rcou_data:
            for motor, channel in self.motor_map.items():
                val = row.get(channel)
                time = row.get("TimeUS")

                if val is not None and time is not None:
                    motor_outputs[motor].append({
                        "t": time,
                        "pwm": val
                    })

        return motor_outputs
    # Esc instance mapping
    # TODO: Esc instance for motor.

    def get_esc_rpm(self):
        if not self.esc_data:
            return {}

        esc_map = {}

        for row in self.esc_data:
            idx = row.get("Instance")
            if idx is None:
                idx = row.get("I")
            rpm = row.get("RPM")

            time = row.get("TimeUS")

            if idx is not None and rpm is not None and time is not None:
                esc_map.setdefault(f"Motor{idx+1}", []).append({
                    "t": time,
                    "rpm": rpm
                })

        return esc_map

    def build_motor_data(self):
        rcou_outputs = self.get_motor_outputs()
        esc_outputs = self.get_esc_rpm()

        return {
            "mapping": self.motor_map,
            "control": {
                "rcou": rcou_outputs
            },
            "feedback": {
                "esc": esc_outputs,
                "rpm": self.rpm_data if self.rpm_data is not None else []
            },
            "power": {
                "bat": self.bat_data or [],
                "powr": self.powr_data or []
            },
            "interaction": {
                "motb": self.motb_data or []
            }
        }

class SensorData:
    def __init__(self, imu_data=None, vibe_data=None, gyr_data=None, mag_data=None):
        self.imu_data = imu_data or []
        self.vibe_data = vibe_data or []
        self.gyro_data = gyr_data or []
        self.mag_data = mag_data or []

    def get_imu(self):
        imu_map = {}
        
        for row in self.imu_data:
            idx = row.get("Instance")
            if idx is None:
                idx = row.get("I")
            if idx is None:
                idx = 0
                
            t = row.get("TimeUS")

            acc = [row.get("AccX"), row.get("AccY"), row.get("AccZ")]
            gyro = [row.get("GyrX"), row.get("GyrY"), row.get("GyrZ")]

            if t is None or None in acc or None in gyro:
                continue
            
            key = f"IMU_{idx}"
            imu_map.setdefault(key, []).append({
                "t": t,
                "acc": acc,
                "gyro": gyro
            })
            
        return imu_map

if __name__ == "__main__":
    parser = BinIngest("old_versions/ardupilot-log-analyzer/data/raw_logs/motor_fail_00000082.BIN")
    
    # parser.save("parsed.json", result)
    result = parser.run()

    print(f"[signals] {', '.join(f'{k}={len(v)}' for k, v in result['data'].items())}")

    motor_mapper = MotorData(
        parm_data=result["data"].get("PARM", []),
        rcou_data=result["data"].get("RCOU", []),
        esc_data=result["data"].get("ESC"),
        motb_data=result["data"].get("MOTB"),
        bat_data=result["data"].get("BAT"),
        powr_data=result["data"].get("POWR"),
        rpm_data=result["data"].get("RPM")
    )

    motor_mapper.build_mapping()
    motor_data = motor_mapper.build_motor_data()

    mapping = motor_data["mapping"]
    rcou    = motor_data["control"]["rcou"]
    esc     = motor_data["feedback"]["esc"]
    rpm     = motor_data["feedback"]["rpm"]
    bat     = motor_data["power"]["bat"]
    powr    = motor_data["power"]["powr"]
    motb    = motor_data["interaction"]["motb"]

    print(f"[mapping]     {mapping}")
    print(f"[control]     rcou={list(rcou.keys()) if rcou else []}")
    print(f"[feedback]    esc={list(esc.keys()) if esc else []}  rpm={'yes' if rpm else 'no'}")
    print(f"[power]       bat={'yes' if bat else 'no'}  powr={'yes' if powr else 'no'}")
    print(f"[interaction] motb={'yes' if motb else 'no'}")

    final_output = {
    "signals": result["data"],
    "motor_data": motor_data
    }

    with open("final_mot_op.json", "w") as file:
        json.dump(final_output, file, indent=2)
    
    # Save complete motor data to json.
    # with open("motor_data.json", "w") as f:
    #     json.dump(motor_data, f, indent=2)
    # print("motor data saved")