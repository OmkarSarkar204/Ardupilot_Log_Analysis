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
MAVLINK_SYSID_MAX = 2**24
MAVLINK_COMPID_MAX = 2**8
MAV_PARAM_TYPE_REAL32 = 9



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


