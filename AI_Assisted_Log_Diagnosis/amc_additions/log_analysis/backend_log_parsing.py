"""
A parser for ArduPilot .bin log files.

The ArduPilot .bin format is self contained: FMT messages define the schema of every message type.
Pymavlink reads those FMT definitions and decodes each message accordingly.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

import contextlib
from typing import Any

from pymavlink import mavutil


def open_log(logfile: str) -> mavutil.mavfile:
    """
    Open an ArduPilot log file.

    Args:
        logfile: The path to an ArduPilot .bin log file.

    Returns:
        A mavutil.mavfile connection object.

    """
    try:
        mlog = mavutil.mavlink_connection(logfile)
    except Exception as e:
        msg = f"Error opening the {logfile} logfile: {e!s}"
        raise OSError(msg) from e
    return mlog  # pyright: ignore[reportReturnType]


def close_log(mlog: mavutil.mavfile) -> None:
    """
    Close an ArduPilot log file.

    Args:
        mlog: The mavutil.mavfile connection to close.

    """
    with contextlib.suppress(OSError):
        mlog.close()


def parse_log(logfile: str) -> Any:  # noqa: ANN401
    """
    Open a log and yield each DataFlash message.

    Each message is yielded as decoded by pymavlink (using the file's own FMT
    definitions) and discarded.

    Args:
        logfile: The path to an ArduPilot .bin log file.

    Yields:
        One DataFlash log message per iteration.

    """
    mlog = open_log(logfile)
    try:
        while True:
            msg = mlog.recv_match()
            if msg is None:
                break
            yield msg
    finally:
        close_log(mlog)
