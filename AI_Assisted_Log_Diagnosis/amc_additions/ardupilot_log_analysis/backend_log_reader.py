from pymavlink import mavutil
from ardupilot_methodic_configurator.data_model_par_dict import ParDict
from ardupilot_methodic_configurator.data_model_vehicle_project_creator import VehicleProjectCreator
from ardupilot_methodic_configurator import extract_param_defaults


class LogData:
  def __init__(self):
    self.messages = {}
    self.default_params = None
    self.firmware_info = None
    self.current_params = None
    self.vehicle_name = None
    self.frame_type = None


class LogReader:
  def __init__(self, logfile: str):
    self.logfile = logfile

  def extract_firmware_info(self) -> tuple[str, int, int, int]:
    return VehicleProjectCreator.extract_firmware_version_from_bin_log(self.logfile)

  def extract_parameters(self) -> tuple[ParDict, ParDict]:
    return VehicleProjectCreator.extract_param_files_from_bin_log(self.logfile)

  def read_all_messages(self) -> LogData:
    log_data = LogData()
    message_counts = {}

    try:
      mlog = mavutil.mavlink_connection(self.logfile)
    except Exception as e:
      msg = f"Error opening the {self.logfile} logfile: {e!s}"
      raise SystemExit(msg) from e

    while True:
      msg = mlog.recv_match()

      if msg is None:
        break

      msg_type = msg.get_type()
      if msg_type not in message_counts:
        message_counts[msg_type] = 0
      message_counts[msg_type] += 1
      if msg.get_type() == "IMU":
        print(msg)
        print(msg.to_dict())
        break



    log_data.firmware_info = self.extract_firmware_info()
    (
    log_data.default_params,
    log_data.current_params,
    ) = self.extract_parameters()

    frame_type_par = log_data.current_params.get("FRAME_TYPE")
    if frame_type_par is not None:
      log_data.frame_type = int(frame_type_par.value)


    log_data.messages = message_counts


    return log_data


if __name__ == "__main__":
  reader = LogReader("altitude_estimation_4.7.bin")
  data = reader.read_all_messages()
  print(type(data))
  print(data.firmware_info)
  print(data.vehicle_name)
  print(data.frame_type)
  print(type(data.default_params))
  print(type(data.current_params))
  print(data.messages)
  print("Total messages:", sum(data.messages.values()))
  print("NONE-type (malformed records):", data.messages.get("NONE", 0))
