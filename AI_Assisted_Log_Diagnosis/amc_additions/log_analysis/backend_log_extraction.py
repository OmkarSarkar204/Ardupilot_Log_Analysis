"""
Parses an ArduPilot .bin log file, and extracts all the parameters required for analysing the log.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

import contextlib
import logging
import re
from typing import Any

from pymavlink import mavutil

PARAM_NAME_REGEX = r"^[A-Z][A-Z_0-9]*$"
PARAM_NAME_MAX_LEN = 16


def is_param_name_too_long(pname: str) -> bool:
    """Return True if the param name exceeds PARAM_NAME_MAX_LEN."""
    return len(pname) > PARAM_NAME_MAX_LEN


def is_param_name_format_valid(pname: str) -> bool:
    """Return True if the parameter name matches the PARAM_NAME_REGEX pattern."""
    return bool(re.match(PARAM_NAME_REGEX, pname))


def open_log(logfile: str) -> mavutil.mavfile:
    """
    Open an ArduPilot log file.

    Args:
      logfile: The path to an Ardupilot .bin log file.

    Returns:
      A mavutil.mavfile connection object.

    """
    try:
        mlog = mavutil.mavlink_connection(logfile)
    except Exception as e:
        msg = f"Error opening the {logfile} logfile: {e!s}"
        raise OSError(msg) from e
    return mlog  # pyright: ignore[reportReturnType]  # pymavlink stubs include CSVReader which doesn't extend mavfile


def close_log(mlog: mavutil.mavfile) -> None:
    """
    Close an ArduPilot log file.

    Args:
      mlog: The mavutil.mavfile connection to close.

    """
    with contextlib.suppress(OSError):
        mlog.close()


class BatteryData:  # pylint: disable=too-many-instance-attributes,too-few-public-methods
    """Stores battery telemetry data extracted from BAT log messages."""

    # BCL will be added later during the Phy Validation

    def __init__(self) -> None:
        self.time_us: list[int] = []
        self.volt: list[float] = []
        self.volt_r: list[float] = []
        self.curr: list[float] = []
        self.curr_tot: list[float] = []
        self.enrg_tot: list[float] = []
        self.temp: list[float] = []
        self.res: list[float] = []
        self.rem_pct: list[float] = []  # stored as float in some firmware versions
        self.health: list[int] = []
        self.state_health: list[int] = []

class PMData: # pylint: disable=too-many-instance-attributes
    """Stores Flight Controller's CPU performance telemetry data extracted from PM messages."""

    def __init__(self) -> None:
        self.time_us: list[int] = []
        self.load: list[int] = []
        self.mem: list[int] = []
        self.loop_rate: list[int] = []
        self.int_err_bitmask: list[int] = []
        self.long_loops: list[int] = []

class IMUData:
    """Stores Inertial Measurement Unit data extracted from IMU messages."""

    def __init__(self) -> None:
        self.time_us: list[int] = []
        self.gyr_x: list[float] = []
        self.gyr_y: list[float] = []
        self.gyr_z: list[float] = []
        self.acc_x: list[float] = []
        self.acc_y: list[float] = []
        self.acc_z: list[float] = []
        self.err_gyro: list[float] = []
        self.err_acc: list[float] = []
        self.temp: list[float] = []
        self.gyro_hlt: list[int] = []
        self.acc_hlt: list[int] = []
        self.gyro_rate: list[int] = []
        self.acc_rate: list[int] = []

class VibeData:
    """Stores Processed Vibration Information data extracted from VIBE messages."""

    def __init__(self) -> None:
        self.time_us: list[int] = []
        self.vibe_x: list[float] = []
        self.vibe_y: list[float] = []
        self.vibe_z: list[float] = []
        self.clip: list[int] = []

class LogData:  # pylint: disable=too-few-public-methods
    """Contains all data extracted from an ArduPilot .bin log."""

    def __init__(self) -> None:
        self.messages: dict[str, int] = {}
        self.default_params: dict[str, float] = {}
        self.current_params: dict[str, float] = {}
        self.firmware_info: tuple[str, int, int, int] | None = None
        self.frame_type: int | None = None
        # There could be multiple batteries in the vehicle, so create a separate dict for them.
        self.batteries: dict[int, BatteryData] = {}
        self.performance_monitor = PMData()
        self.imu_data: dict[int, IMUData] = {}
        self.vibe_data: dict[int, VibeData] = {}


def extract_log(logfile: str) -> LogData:
    """
    Open the log file, scan every message, and return the LogData.

    Args:
        logfile: The path to an ArduPilot .bin log file.

    Returns:
        A populated LogData object containing parameters, firmware info, message counts, and frame type.

    """
    log_data = LogData()
    message_counts: dict[str, int] = {}
    firmware_from_ver: tuple[str, int, int, int] | None = None
    firmware_from_msg: tuple[str, int, int, int] | None = None

    mlog = open_log(logfile)

    try:
        while True:
            msg = mlog.recv_match()
            if msg is None:
                break
            msg_type = msg.get_type()
            message_counts[msg_type] = message_counts.get(msg_type, 0) + 1

            # Extract PARM messages and store them, also is used in extract_param_defaults.py
            if msg_type == "PARM":
                process_param(msg, log_data)

            # Extract the Version with Vehicle_type, Major, Minor and Patch.
            elif msg_type == "VER":
                firmware_from_ver = process_ver(msg)

            # Fallback to MSG if version is not available.
            elif msg_type == "MSG":
                firmware_from_msg = process_msg_version_fallback(msg, firmware_from_msg)

            # Extract the BAT messages and store them in BatteryData
            elif msg_type == "BAT":
                process_bat(msg, log_data)

            # Extract the PM messages and store them in PMData
            elif msg_type == "PM":
                process_performance(msg, log_data)

            # Extract IMU messages and store them in IMUData
            elif msg_type == "IMU":
                process_imu(msg, log_data)

            elif msg_type == "VIBE":
                process_vibe(msg, log_data)

        if firmware_from_ver is not None:
            log_data.firmware_info = firmware_from_ver
        else:
            log_data.firmware_info = firmware_from_msg

        process_frame_type(log_data)
        log_data.messages = message_counts

    finally:
        close_log(mlog)

    return log_data


def process_bat(msg: Any, log_data: LogData) -> None:  # noqa: ANN401
    """
    Extract battery telemetry from a BAT DataFlash log entry.

    Args:
        msg: A BAT log entry object parsed from an ArduPilot .bin file
             (returned by mavutil.mavfile.recv_match()).
        log_data: The LogData instance to write battery data into.

    """
    # If there are multiple battery instances store them separately
    bat_inst = int(msg.Inst)
    if bat_inst not in log_data.batteries:
        log_data.batteries[bat_inst] = BatteryData()
    battery = log_data.batteries[bat_inst]

    battery.time_us.append(int(msg.TimeUS))
    battery.volt.append(float(msg.Volt))
    battery.volt_r.append(float(msg.VoltR))
    battery.curr.append(float(msg.Curr))
    battery.curr_tot.append(float(msg.CurrTot))
    battery.enrg_tot.append(float(msg.EnrgTot))
    battery.temp.append(float(msg.Temp))
    battery.res.append(float(msg.Res))
    # RemPct is stored as float in some firmware versions; preserve precision
    battery.rem_pct.append(float(msg.RemPct))
    # H (health) and SH (state health) may be absent in older firmware; default to 0
    battery.health.append(int(getattr(msg, "H", 0)))
    battery.state_health.append(int(getattr(msg, "SH", 0)))

def process_performance(msg: Any, log_data: LogData) -> None:  # noqa: ANN401
    """
    Extract performance telemetry from a PM DataFlash log entry.

    Args:
        msg: A PM log entry object parsed from an ArduPilot .bin file
             (returned by mavutil.mavfile.recv_match()).
        log_data: The LogData instance to write performance data into.

    """
    pm = log_data.performance_monitor

    pm.time_us.append(int(msg.TimeUS))
    pm.load.append(int(msg.Load))
    pm.mem.append(int(msg.Mem))
    pm.loop_rate.append(int(msg.LR))
    # InE renamed from IntE between firmware 4.5.4 and 4.7.0.
    pm.int_err_bitmask.append(int(getattr(msg, "InE", getattr(msg, "IntE", 0))))
    pm.long_loops.append(int(msg.NLon))

def process_imu(msg: Any, log_data: LogData) -> None:  # noqa: ANN401
    """
    Extract inertial Data from an IMU DataFlash log entry.

    Args:
        msg: An IMU log entry object parsed from an ArduPilot .bin file
             (returned by mavutil.mavfile.recv_match()).
        log_data: The LogData instance to write IMU data into.

    """
    imu_inst = int(msg.I)
    if imu_inst not in log_data.imu_data:
        log_data.imu_data[imu_inst] = IMUData()
    imu = log_data.imu_data[imu_inst]

    imu.time_us.append(int(msg.TimeUS))
    imu.gyr_x.append(float(msg.GyrX))
    imu.gyr_y.append(float(msg.GyrY))
    imu.gyr_z.append(float(msg.GyrZ))
    imu.acc_x.append(float(msg.AccX))
    imu.acc_y.append(float(msg.AccY))
    imu.acc_z.append(float(msg.AccZ))
    imu.err_gyro.append(float(msg.EG))
    imu.err_acc.append(float(msg.EA))
    imu.temp.append(float(msg.T))
    imu.gyro_hlt.append(int(getattr(msg, "GH", 0)))
    imu.acc_hlt.append(int(getattr(msg, "AH", 0)))
    imu.gyro_rate.append(int(msg.GHz))
    imu.acc_rate.append(int(msg.AHz))

def process_vibe(msg: Any, log_data: LogData) -> None: # noqa: ANN401
    vibe_inst = int(msg.IMU)
    if vibe_inst not in log_data.vibe_data:
        log_data.vibe_data[vibe_inst] = VibeData()
    vibe = log_data.vibe_data[vibe_inst]

    vibe.time_us.append(int(msg.TimeUS))
    vibe.vibe_x.append(float(msg.VibeX))
    vibe.vibe_y.append(float(msg.VibeY))
    vibe.vibe_z.append(float(msg.VibeZ))
    vibe.clip.append(int(msg.Clip))

def process_param(msg: Any, log_data: LogData) -> None:  # noqa: ANN401
    """
    Validate and store a single PARM log entry into log_data's parameter dicts.

    Each of default_params and current_params is populated independently from the
    first PARM occurrence that carries a non-None value for that field.  Entries
    with invalid or overly long names are skipped with a warning.  Once both
    dicts contain a value for a given name, further occurrences are ignored.

    Args:
      msg: A PARM log entry object parsed from an ArduPilot .bin file
           (returned by mavutil.mavfile.recv_match()).
      log_data: The LogData instance to write param values into.

    """
    pname = str(msg.Name)
    if is_param_name_too_long(pname):
        logging.warning("Too long parameter name %s", pname)
        return
    if not is_param_name_format_valid(pname):
        logging.warning("Invalid parameter name %s", pname)
        return
    already_has_default = pname in log_data.default_params
    already_has_current = pname in log_data.current_params
    if already_has_default and already_has_current:
        return
    if not already_has_default and msg.Default is not None:
        log_data.default_params[pname] = float(msg.Default)
    if not already_has_current and msg.Value is not None:
        log_data.current_params[pname] = float(msg.Value)


def process_ver(msg: Any) -> tuple[str, int, int, int] | None:  # noqa: ANN401
    """
    Extract firmware version from a VER DataFlash log entry.

    Args:
      msg: A VER log entry object parsed from an ArduPilot .bin file
           (returned by mavutil.mavfile.recv_match()).

    Returns:
      A tuple of (vehicle_type, major, minor, patch), e.g. ("ArduCopter", 4, 6, 3),
      or None if any version field is missing or vehicle_type cannot be determined.

    """
    fws = str(msg.FWS)  # e.g. "ArduCopter V4.6.3"
    parts = fws.split(maxsplit=1)
    vehicle_type = parts[0] if parts else ""
    if not vehicle_type:
        return None
    maj, mini, pat = msg.Maj, msg.Min, msg.Pat
    if maj is None or mini is None or pat is None:
        return None

    return (vehicle_type, int(maj), int(mini), int(pat))


def process_msg_version_fallback(
    msg: Any,  # noqa: ANN401
    firmware_from_msg: tuple[str, int, int, int] | None,
) -> tuple[str, int, int, int] | None:
    """
    Extract firmware version from a MSG DataFlash log entry.

    Falls back to scanning MSG messages until one with a parseable "Vx.y" version
    is found (e.g. "ArduCopter V4.6.3 (hash)").

    Args:
      msg: A MSG log entry object parsed from an ArduPilot .bin file
           (returned by mavutil.mavfile.recv_match()).
      firmware_from_msg: A previously found result from a MSG entry, or None.

    Returns:
      The existing result unchanged if already found, a newly parsed tuple
      of (vehicle_type, major, minor, patch) if parseable, or None otherwise.

    """
    if firmware_from_msg is not None:
        return firmware_from_msg
    parts = str(msg.Message).split()
    if len(parts) >= 2 and parts[1].startswith("V"):
        version_parts = parts[1][1:].split(".")  # Remove "V" prefix, split by "."
        if len(version_parts) >= 2:
            with contextlib.suppress(ValueError):
                patch_val = int(version_parts[2]) if len(version_parts) >= 3 else 0
                return (parts[0], int(version_parts[0]), int(version_parts[1]), patch_val)
    return None


def process_frame_type(log_data: LogData) -> None:
    """
    Extract the Frame Type from the FRAME_TYPE parameter.

    Args:
        log_data: The LogData instance whose current_params are read from.

    """
    frame_type_val = log_data.current_params.get("FRAME_TYPE")
    if frame_type_val is not None:
        log_data.frame_type = int(frame_type_val)
    else:
        logging.debug("FRAME_TYPE parameter not found in log; frame_type remains None")

if __name__ == "__main__":
    data = extract_log("altitude_estimation_4.7.bin")
    print("IMU Instances:", list(data.imu_data.keys()))

    # for inst, imu in data.imu_data.items():
    #     print(f"\nIMU {inst}")
    #     print("Samples:", len(imu.time_us))
    #     print("First TimeUS:", imu.time_us[0])
    #     print("Last TimeUS:", imu.time_us[-1])

    #     print("Gyro X Range:", min(imu.gyr_x), max(imu.gyr_x))
    #     print("Gyro Y Range:", min(imu.gyr_y), max(imu.gyr_y))
    #     print("Gyro Z Range:", min(imu.gyr_z), max(imu.gyr_z))

    #     print("Accel X Range:", min(imu.acc_x), max(imu.acc_x))
    #     print("Accel Y Range:", min(imu.acc_y), max(imu.acc_y))
    #     print("Accel Z Range:", min(imu.acc_z), max(imu.acc_z))

    #     print("Max Gyro Errors:", max(imu.err_gyro))
    #     print("Max Accel Errors:", max(imu.err_acc))

    #     print("Unique Gyro Health:", set(imu.gyro_hlt))
    #     print("Unique Accel Health:", set(imu.acc_hlt))

    #     print("Gyro Rate:", set(imu.gyro_rate))
    #     print("Accel Rate:", set(imu.acc_rate))

    # pm = data.performance_monitor

    # print("PM Samples:", len(pm.time_us))

    # if pm.time_us:
    #     print("First TimeUS:", pm.time_us[0])
    #     print("Last TimeUS:", pm.time_us[-1])

    #     print("Max CPU Load:", max(pm.load))
    #     print("Average CPU Load:", sum(pm.load) / len(pm.load))

    #     print("Minimum Free Memory:", min(pm.mem))

    #     print("Max Long Loops:", max(pm.long_loops))

    #     print("Internal Errors Seen:", any(mask != 0 for mask in pm.int_err_bitmask))
    #     print(data.messages["PM"])
    #     print(len(data.performance_monitor.time_us))
    #     print(set(data.performance_monitor.int_err_bitmask))
    # batt = data.batteries.get(0)
    # if batt:
    #     print(len(batt.timeUS))
    #     print(batt.volt[0])
    #     print(min(batt.timeUS))
    #     print(max(batt.timeUS))
    #     print(batt.state_health)


#     print(data.firmware_info)

#     print(len(data.default_params))

#     print(len(data.current_params))

#     non_default = {
#         name: value
#         for name, value in data.current_params.items()
#         if name in data.default_params and value != data.default_params[name]
#     }
#     print(len(non_default))
