from pymavlink import mavutil
import json


class BinIngest:
    def __init__(self, file_path):
        self.file_path = file_path
        self.connection = mavutil.mavlink_connection(file_path)

        self.schema = set()
        
        # RCOU: PWM output signals sent to motors
        # ESC: ESC including RPM 
        # MOTB: Motor thrust and battery intercation data
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
            "ERR", "RPM"
        ]

        self.data = {}
    
    def normalize_value(self, value):
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return value

    def extract_schema(self):
        while True:
            packs = self.connection.recv_match(type='FMT')
            if packs is None:
              break

            self.schema.add(packs.Name)

    def reset(self):
        self.connection = mavutil.mavlink_connection(self.file_path)

    def act_signals(self):
        self.active_signals = [
            s for s in self.targets if s in self.schema
        ]

        self.data = {s: [] for s in self.active_signals}

    def parse(self):
        count = 0

        while True:
            msg = self.connection.recv_match(blocking=True)
            if msg is None:
                break

            count += 1
            mtype = msg.get_type()

            if mtype in self.data:
                try:
                    raw = msg.to_dict()

                    clean = {}
                    for k, v in raw.items():
                        clean[k] = self.normalize_value(v)

                    self.data[mtype].append(clean)

                except Exception:
                    continue

        return count
    
    def norm_time(data):
        for signal in data:
            for row in data[signal]:
                row['TimeUS'] = row['TimeUS'] / 1e6
    
    def run(self):
        self.extract_schema()
        self.reset()
        self.act_signals()
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

if __name__ == "__main__":
    parser = BinIngest("old_versions/ardupilot-log-analyzer/data/raw_logs/motor_fail_00000082.BIN")

    result = parser.run()

    parser.save("parsed.json", result)

    print("Saved parsed.json")

    for k, v in result["data"].items():
        print(f"{k}: {len(v)} entries")