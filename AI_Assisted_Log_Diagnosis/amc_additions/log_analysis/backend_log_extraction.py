"""
Parses an ArduPilot .bin log file and extracts a generic.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later

"""

import contextlib
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
        logfile: Path to a .bin log.

    Returns:
        pymavlink log object.

    """
    try:
        mlog = mavutil.mavlink_connection(logfile)
    except Exception as e:
        msg = f"Error opening logfile {logfile}: {e!s}"
        raise OSError(msg) from e

    return mlog  # pyright: ignore[reportReturnType]


def close_log(mlog: mavutil.mavfile) -> None:
    """Close a log file."""
    with contextlib.suppress(OSError):
        mlog.close()


def parse_log(logfile: str) -> Any:  # noqa: ANN401
    """Yield decoded DataFlash messages one at a time."""
    mlog = open_log(logfile)

    try:
        while True:
            msg = mlog.recv_match()

            if msg is None:
                break

            yield msg

    finally:
        close_log(mlog)


class LogData:
    """
    Generic log representation.

    format:
        Message definitions discovered from FMT/FMTU/UNIT/MULT

    raw_msg:
        Decoded messages grouped by type

    msg_count:
        Count of messages by type
    """

    def __init__(self) -> None:
        self.format: dict[str, Any] = {}

        self.raw_msg: dict[str, list[dict[str, Any]]] = {}

        self.msg_count: dict[str, int] = {}


def extract_log(logfile: str) -> LogData:
    """
    Parse a complete ArduPilot .bin file.

    Returns:
        Populated LogData object.

    """
    log_data = LogData()

    mlog = open_log(logfile)

    try:
        while True:
            msg = mlog.recv_match()

            if msg is None:
                break

            msg_type = msg.get_type()

            log_data.msg_count[msg_type] = log_data.msg_count.get(msg_type, 0) + 1

            log_data.raw_msg.setdefault(
                msg_type,
                [],
            ).append(msg.to_dict())

        for fmt in mlog.formats.values():
            log_data.format[fmt.name] = {
                "name": fmt.name,
                "msg_type": fmt.type,
                "length": fmt.len,
                "format": fmt.format,
                "columns": list(fmt.columns),
                "units": list(fmt.units),
                "msg_mults": list(fmt.msg_mults),
                "msg_types": list(fmt.msg_types),
            }

    finally:
        close_log(mlog)

    return log_data


def process_msg_version_fallback(
msg: Any,  # noqa: ANN401
    firmware_from_msg: tuple[str, int, int, int] | None,
) -> tuple[str, int, int, int] | None:
    """Extract firmware version from MSG raw_msg."""
    if firmware_from_msg is not None:
        return firmware_from_msg

    parts = str(msg.Message).split()

    if len(parts) >= 2 and parts[1].startswith("V"):
        version_parts = parts[1][1:].split(".")

        if len(version_parts) >= 2:
            with contextlib.suppress(ValueError):
                patch_val = int(version_parts[2]) if len(version_parts) >= 3 else 0

                return (
                    parts[0],
                    int(version_parts[0]),
                    int(version_parts[1]),
                    patch_val,
                )

    return None


def process_ver(msg: Any) -> tuple[str, int, int, int] | None:  # noqa: ANN401
    """Extract firmware version from VER raw_msg."""
    fws = str(msg.FWS)

    parts = fws.split(maxsplit=1)

    vehicle_type = parts[0] if parts else ""

    if not vehicle_type:
        return None

    maj, mini, pat = msg.Maj, msg.Min, msg.Pat

    if maj is None or mini is None or pat is None:
        return None

    return (
        vehicle_type,
        int(maj),
        int(mini),
        int(pat),
    )
