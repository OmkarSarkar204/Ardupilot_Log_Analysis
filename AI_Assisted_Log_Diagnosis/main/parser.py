from pymavlink import mavutil
import json


def normalize_value(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


def read_msg(file_path, output_path):
    """
    Reads a .BIN log file and dumps ALL messages into JSON.
    pure raw extraction.
    """

    connection = mavutil.mavlink_connection(file_path)

    all_messages = []

    while True:
        message = connection.recv_match(blocking=False)
        if message is None:
            break

        try:
            raw_dict = message.to_dict()

            clean_dict = {}
            for key, value in raw_dict.items():
                clean_dict[key] = normalize_value(value)

            # explicitly store type
            clean_dict["type"] = message.get_type()

            all_messages.append(clean_dict)

        except Exception:
            # skip only problematic messages safely
            continue

    with open(output_path, "w") as f:
        json.dump(all_messages, f, indent=2)


if __name__ == "__main__":
    input_file = "old_versions/ardupilot-log-analyzer/data/raw_logs/healthy_05.BIN"
    output_file = "output.json"

    read_msg(input_file, output_file)