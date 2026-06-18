"""
Parses an ArduPilot .bin log file, and extracts all the parameters required for analysing the log.

Supports Mission Planner, MAVProxy and QGCS file format output

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

import re
import logging
import contextlib
from pymavlink import mavutil

PARAM_NAME_REGEX = r"^[A-Z][A-Z_0-9]*$"
PARAM_NAME_MAX_LEN = 16

def is_param_name_too_long(pname: str) -> bool:
    return len(pname) > PARAM_NAME_MAX_LEN

def is_param_name_format_valid(pname: str) -> bool:
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
        raise SystemExit(msg) from e
    return mlog  # pyright: ignore[reportReturnType]  # pymavlink stubs include CSVReader which doesn't extend mavfile


def close_log(mlog: mavutil.mavfile) -> None:
    """
    Close an ArduPilot log file.

    Args:
      mlog: The mavutil.mavfile connection to close.

    """
    with contextlib.suppress(OSError):
        mlog.close()


class LogData:
    def __init__(self) -> None:
        self.messages: dict[str, int] = {}
        self.default_params: dict[str, float] = {}
        self.current_params: dict[str, float] = {}
        self.firmware_info: tuple[str, int, int, int] | None = None
        self.frame_type: int | None = None


class LogReader:
    def __init__(self, logfile: str) -> None:
        self.logfile = logfile


    def extract_log(self) -> LogData:
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

                #Extract PARM messages and store them, also is used in extract_param_defaults.py
                if msg_type == "PARM":
                    process_param(msg, log_data)

                # Extract the Version with Vehicle_type, Major, Minor and Patch.
                elif msg_type == "VER":
                    firmware_from_ver = process_ver(msg)

                # Fallback to MSG if version is not available.
                elif msg_type == "MSG":
                    firmware_from_msg = process_msg_version_fallback(msg, firmware_from_msg)
            if firmware_from_ver is not None:
                log_data.firmware_info = firmware_from_ver
            else:
                log_data.firmware_info = firmware_from_msg

            process_frame_type(log_data)

        finally:
            close_log(mlog)
        log_data.messages = message_counts
        return log_data



def process_param(msg: mavutil.mavfile, log_data: LogData) -> None:
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
        fws = str(msg.FWS) # e.g. "ArduCopter V4.6.3"
        vehicle_type = fws.split(maxsplit=1)[0] if fws else ""
        maj, mini, pat = msg.Maj, msg.Min, msg.Pat
        if maj is None or mini is None or pat is None:
            return None

        return (vehicle_type, int(maj), int(mini), int(pat))

def process_msg_version_fallback(msg, firmware_from_msg: tuple[str, int, int, int] | None) -> tuple[str, int, int, int] | None:  # noqa: ANN001
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
        frame_type_val = log_data.current_params.get("FRAME_TYPE")
        if frame_type_val is not None:
            log_data.frame_type = int(frame_type_val)

def process_batt(msg: mavutil.mavfile, log_data: LogData) -> None:
        pass


#This is for testing

# if __name__ == "__main__":
#     reader = LogReader("MethodicConfigurator/altitude_estimation_4.7.bin")
#     data = reader.extract_log()

#     print(data.firmware_info)

#     print(len(data.default_params))

#     print(len(data.current_params))

#     non_default = {
#         name: value
#         for name, value in data.current_params.items()
#         if name in data.default_params
#         and value != data.default_params[name]
#     }
#     print(len(non_default))
