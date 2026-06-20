"""
Parses an ArduPilot .bin log file, and extracts all the parameters required for analysing the log.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

import contextlib
import logging
import re

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

class BatteryData:
    def __init__(self) -> None:
        self.timeUS: list[int] = []
        self.volt: list[float] = []
        self.volt_r: list[float] = []
        self.curr: list[float] = []
        self.curr_tot: list[float] = []
        self.enrg_tot: list[float] = []
        self.temp: list[float] = []
        self.res: list[float] = []
        self.rem_pct: list[int] = []
        self.health: list[int] = []
        self.state_health: list[int] = []


class LogReader:  # pylint: disable=too-few-public-methods
    """Reader for Ardupilot log files, sending each message to its appropriate function."""

    def __init__(self, logfile: str) -> None:
        self.logfile = logfile

    def extract_log(self) -> LogData:
        """
        Open the log file, scan every message, and return the LogData.

        Returns:
            A populated LogData object containing parameters, firmware info, message counts, and frame type.

        """
        log_data = LogData()
        message_counts: dict[str, int] = {}
        firmware_from_ver: tuple[str, int, int, int] | None = None
        firmware_from_msg: tuple[str, int, int, int] | None = None

        mlog = open_log(self.logfile)

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

                elif msg_type == "BAT":
                    process_bat(msg, log_data)

            if firmware_from_ver is not None:
                log_data.firmware_info = firmware_from_ver
            else:
                log_data.firmware_info = firmware_from_msg

            process_frame_type(log_data)

        finally:
            close_log(mlog)
        log_data.messages = message_counts
        return log_data


def process_bat(msg: mavutil.mavfile, log_data: LogData) -> None:

    inst = int(msg.Inst)
    if inst not in log_data.batteries:
        log_data.batteries[inst] = BatteryData()
    battery = log_data.batteries[inst]

    battery.timeUS.append(int(msg.TimeUS))
    battery.volt.append(float(msg.Volt))
    battery.volt_r.append(float(msg.VoltR))
    battery.curr.append(float(msg.Curr))
    battery.curr_tot.append(float(msg.CurrTot))
    battery.enrg_tot.append(float(msg.EnrgTot))
    battery.temp.append(float(msg.Temp))
    battery.res.append(float(msg.Res))
    battery.rem_pct.append(int(msg.RemPct))
    battery.health.append(int(msg.H))
    battery.state_health.append(int(msg.SH))

def process_param(msg: mavutil.mavfile, log_data: LogData) -> None:
    """
    Validate and store a single PARM message into log_data's parameter dicts.

    Skips entries with invalid or duplicate names. Adds both
    default_params and current_params from the message's Default and Value fields.

    Args:
      msg: A PARM log entry parsed from an ArduPilot .bin file.
      log_data: The LogData instance to write param value into.

    """
    pname = str(msg.Name)
    if is_param_name_too_long(pname):
        logging.warning("Too long parameter name %s", pname)
        return
    if not is_param_name_format_valid(pname):
        logging.warning("Invalid parameter name %s", pname)
        return
    if pname in log_data.default_params:
        return
    if msg.Default is not None:
        log_data.default_params[pname] = float(msg.Default)
    if msg.Value is not None:
        log_data.current_params[pname] = float(msg.Value)


def process_ver(msg: mavutil.mavfile) -> tuple[str, int, int, int] | None:
    """
    Extract firmware version from VER message.

    Args:
      msg: A VER log entry parsed from an ArduPilot .bin file.

    Returns:
      A tuple of (vehicle_type, major, minor, patch), e.g. ("ArduCopter", 4, 6, 3).

    """
    fws = str(msg.FWS)  # e.g. "ArduCopter V4.6.3"
    vehicle_type = fws.split(maxsplit=1)[0] if fws else ""
    maj, mini, pat = msg.Maj, msg.Min, msg.Pat
    if maj is None or mini is None or pat is None:
        return None

    return (vehicle_type, int(maj), int(mini), int(pat))


def process_msg_version_fallback(
    msg: mavutil.mavfile, firmware_from_msg: tuple[str, int, int, int] | None
) -> tuple[str, int, int, int] | None:
    """
    Extract firmware version from MSG message.

    Falls back to scanning MSG messages until one with a parseable "Vx.y" version
    is found (e.g. "ArduCopter V4.6.3 (hash)").

    Args:
      msg: A MSG log entry parsed from an ArduPilot .bin file.
      firmware_from_msg: If any previously found message from MSG, or None.

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


if __name__ == "__main__":
    reader = LogReader("altitude_estimation_4.7.bin")
    data = reader.extract_log()
    batt = data.batteries.get(0)
    if batt:
        print(len(batt.timeUS))
        print(batt.volt[0])
        print(min(batt.timeUS))
        print(max(batt.timeUS))
        print(batt.state_health)


#     print(data.firmware_info)

#     print(len(data.default_params))

#     print(len(data.current_params))

#     non_default = {
#         name: value
#         for name, value in data.current_params.items()
#         if name in data.default_params and value != data.default_params[name]
#     }
#     print(len(non_default))
