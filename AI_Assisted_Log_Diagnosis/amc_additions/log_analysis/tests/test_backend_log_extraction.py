#!/usr/bin/env python3

"""
Tests for ardupilot_methodic_configurator/log_analysis/backend_log_extraction.py.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

from unittest.mock import MagicMock, patch

import pytest

from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import (
    LogData,
    close_log,
    extract_log,
    is_param_name_format_valid,
    is_param_name_too_long,
    open_log,
    process_bat,
    process_frame_type,
    process_msg_version_fallback,
    process_param,
    process_ver,
)

# pylint: disable=missing-class-docstring, redefined-outer-name

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_log_data() -> LogData:
    """Fixture providing a fresh, empty LogData instance for each test."""
    return LogData()


@pytest.fixture
def mock_mlog() -> MagicMock:
    """Fixture providing a mock mavutil connection that yields no messages by default."""
    conn = MagicMock()
    conn.recv_match.return_value = None
    return conn


@pytest.fixture
def bat_msg() -> MagicMock:
    """Fixture providing a realistic BAT log entry for instance 0 with known values."""
    msg = MagicMock()
    msg.Inst = 0
    msg.TimeUS = 1_000_000
    msg.Volt = 16.8
    msg.VoltR = 16.5
    msg.Curr = 10.5
    msg.CurrTot = 105.0
    msg.EnrgTot = 1764.0
    msg.Temp = 28.3
    msg.Res = 0.012
    msg.RemPct = 94.5
    msg.H = 1
    msg.SH = 1
    return msg


def _make_msg(**kwargs: object) -> MagicMock:
    """Return a MagicMock whose attributes are set from kwargs."""
    msg = MagicMock()
    for k, v in kwargs.items():
        setattr(msg, k, v)
    return msg


def _make_log_msg(msg_type: str, **kwargs: object) -> MagicMock:
    """Return a MagicMock DataFlash log entry with a get_type() and given attributes."""
    msg = _make_msg(**kwargs)
    msg.get_type.return_value = msg_type
    return msg


def _make_parm_msg(name: str, default: float | None, value: float | None) -> MagicMock:
    """Return a PARM DataFlash log entry with the given name, default and value."""
    return _make_log_msg("PARM", Name=name, Default=default, Value=value)


def _make_ver_msg(vehicle: str = "ArduCopter", maj: int = 4, min_: int = 6, pat: int = 3) -> MagicMock:
    """Return a VER DataFlash log entry with the given firmware version fields."""
    return _make_log_msg("VER", FWS=f"{vehicle} V{maj}.{min_}.{pat}", Maj=maj, Min=min_, Pat=pat)


# ---------------------------------------------------------------------------
# is_param_name_too_long
# ---------------------------------------------------------------------------


class TestIsParamNameTooLong:
    def test_typical_ardu_param_name_is_accepted(self) -> None:
        """
        Short ArduPilot parameter names are not rejected as too long.

        GIVEN: A standard parameter name within the 16-character limit
        WHEN: is_param_name_too_long is called
        THEN: It returns False so the caller proceeds normally
        """
        assert is_param_name_too_long("ATC_RAT_RLL_P") is False

    def test_param_name_at_exact_length_limit_is_accepted(self) -> None:
        """
        Parameter names of exactly 16 characters are valid.

        GIVEN: A parameter name that is exactly 16 characters long
        WHEN: is_param_name_too_long is called
        THEN: It returns False because 16 == PARAM_NAME_MAX_LEN is allowed
        """
        assert is_param_name_too_long("A" * 16) is False

    def test_param_name_exceeding_limit_is_rejected(self) -> None:
        """
        Parameter names longer than 16 characters are flagged as invalid.

        GIVEN: A parameter name with 17 characters (one over the limit)
        WHEN: is_param_name_too_long is called
        THEN: It returns True so the caller can skip or warn about it
        """
        assert is_param_name_too_long("A" * 17) is True


# ---------------------------------------------------------------------------
# is_param_name_format_valid
# ---------------------------------------------------------------------------


class TestIsParamNameFormatValid:
    def test_standard_uppercase_param_name_is_valid(self) -> None:
        """
        Standard ArduPilot parameter names with uppercase letters and underscores are accepted.

        GIVEN: A well-formed parameter name starting with an uppercase letter
        WHEN: is_param_name_format_valid is called
        THEN: It returns True so the parameter is stored
        """
        assert is_param_name_format_valid("ATC_RAT_RLL_P") is True

    def test_param_name_starting_with_digit_is_rejected(self) -> None:
        """
        Parameter names beginning with a digit violate the naming convention.

        GIVEN: A parameter name that starts with a digit
        WHEN: is_param_name_format_valid is called
        THEN: It returns False to reject the malformed name
        """
        assert is_param_name_format_valid("1INVALID") is False

    def test_lowercase_param_name_is_rejected(self) -> None:
        """
        ArduPilot parameter names must be uppercase; lowercase names are invalid.

        GIVEN: A parameter name in lowercase
        WHEN: is_param_name_format_valid is called
        THEN: It returns False so the malformed entry is skipped
        """
        assert is_param_name_format_valid("atc_p") is False

    def test_single_uppercase_letter_is_a_valid_param_name(self) -> None:
        """
        A single uppercase letter satisfies the minimum valid parameter name format.

        GIVEN: A single-character uppercase name
        WHEN: is_param_name_format_valid is called
        THEN: It returns True because the regex allows it
        """
        assert is_param_name_format_valid("A") is True

    def test_param_name_with_special_chars_is_rejected(self) -> None:
        """
        Parameter names containing special characters are rejected.

        GIVEN: A parameter name that contains a hyphen
        WHEN: is_param_name_format_valid is called
        THEN: It returns False because only A-Z, 0-9 and _ are allowed
        """
        assert is_param_name_format_valid("ATC-P") is False


# ---------------------------------------------------------------------------
# open_log
# ---------------------------------------------------------------------------


class TestOpenLog:
    def test_valid_bin_file_path_yields_connection(self) -> None:
        """
        Opening an existing log file returns the mavutil connection for reading.

        GIVEN: A .bin log file path that mavutil can open
        WHEN: open_log is called
        THEN: The returned object is the mavutil connection, ready for recv_match
        """
        mock_conn = MagicMock()
        with patch(
            "ardupilot_methodic_configurator.log_analysis.backend_log_extraction.mavutil.mavlink_connection",
            return_value=mock_conn,
        ):
            result = open_log("dummy.bin")
        assert result is mock_conn

    def test_missing_file_raises_oserror_with_informative_message(self) -> None:
        """
        A missing or unreadable log file raises OSError so callers can report the problem.

        GIVEN: A log file path that mavutil cannot open
        WHEN: open_log is called
        THEN: OSError is raised with the file name in the message
        """
        with (
            patch(
                "ardupilot_methodic_configurator.log_analysis.backend_log_extraction.mavutil.mavlink_connection",
                side_effect=FileNotFoundError("no such file"),
            ),
            pytest.raises(OSError, match=r"Error opening the dummy\.bin logfile"),
        ):
            open_log("dummy.bin")

    def test_permission_error_is_also_wrapped_in_oserror(self) -> None:
        """
        Any exception from mavutil (not just FileNotFoundError) is wrapped in OSError.

        GIVEN: mavutil raises PermissionError when trying to open the file
        WHEN: open_log is called
        THEN: OSError is raised with the file name in the message
        """
        with (
            patch(
                "ardupilot_methodic_configurator.log_analysis.backend_log_extraction.mavutil.mavlink_connection",
                side_effect=PermissionError("access denied"),
            ),
            pytest.raises(OSError, match=r"Error opening the dummy\.bin logfile"),
        ):
            open_log("dummy.bin")


# ---------------------------------------------------------------------------
# close_log
# ---------------------------------------------------------------------------


class TestCloseLog:
    def test_log_connection_is_closed_after_extraction(self) -> None:
        """
        close_log closes the underlying connection to release file handles.

        GIVEN: An open mavutil connection
        WHEN: close_log is called
        THEN: The connection's close() method is called exactly once
        """
        mock_conn = MagicMock()
        close_log(mock_conn)
        mock_conn.close.assert_called_once()

    def test_already_closed_connection_does_not_raise(self) -> None:
        """
        Closing an already-closed connection is safe and does not propagate errors.

        GIVEN: A connection whose close() raises OSError (already closed)
        WHEN: close_log is called
        THEN: No exception propagates; the error is silently suppressed
        """
        mock_conn = MagicMock()
        mock_conn.close.side_effect = OSError("already closed")
        close_log(mock_conn)  # must not raise

    def test_non_oserror_from_close_propagates(self) -> None:
        """
        Only OSError is suppressed; unexpected exceptions from close() must propagate.

        GIVEN: A connection whose close() raises RuntimeError
        WHEN: close_log is called
        THEN: RuntimeError propagates so the caller is aware of the unexpected failure
        """
        mock_conn = MagicMock()
        mock_conn.close.side_effect = RuntimeError("unexpected")
        with pytest.raises(RuntimeError):
            close_log(mock_conn)


# ---------------------------------------------------------------------------
# process_ver
# ---------------------------------------------------------------------------


class TestProcessVer:
    def test_well_formed_ver_entry_yields_vehicle_and_version(self) -> None:
        """
        A complete VER log entry produces the vehicle type and numeric version tuple.

        GIVEN: A VER DataFlash entry with FWS="ArduCopter V4.6.3" and Maj/Min/Pat set
        WHEN: process_ver is called
        THEN: A tuple ("ArduCopter", 4, 6, 3) is returned for downstream use
        """
        msg = _make_msg(FWS="ArduCopter V4.6.3", Maj=4, Min=6, Pat=3)
        assert process_ver(msg) == ("ArduCopter", 4, 6, 3)

    def test_ver_entry_with_missing_major_version_is_ignored(self) -> None:
        """
        A VER entry missing the major version field cannot be used for version detection.

        GIVEN: A VER DataFlash entry where Maj is None
        WHEN: process_ver is called
        THEN: None is returned so the caller falls back to MSG scanning
        """
        msg = _make_msg(FWS="ArduCopter V4.6.3", Maj=None, Min=6, Pat=3)
        assert process_ver(msg) is None

    def test_ver_entry_with_empty_firmware_string_is_ignored(self) -> None:
        """
        A VER entry with an empty FWS field cannot identify the vehicle type.

        GIVEN: A VER DataFlash entry where FWS is an empty string
        WHEN: process_ver is called
        THEN: None is returned because vehicle_type cannot be determined
        """
        msg = _make_msg(FWS="", Maj=4, Min=6, Pat=3)
        assert process_ver(msg) is None

    def test_ver_entry_with_missing_minor_version_is_ignored(self) -> None:
        """
        A VER entry missing the minor version field cannot produce a complete tuple.

        GIVEN: A VER DataFlash entry where Min is None
        WHEN: process_ver is called
        THEN: None is returned so the caller tries the MSG fallback
        """
        msg = _make_msg(FWS="ArduPlane V4.5.0", Maj=4, Min=None, Pat=0)
        assert process_ver(msg) is None

    def test_ver_entry_with_missing_patch_version_is_ignored(self) -> None:
        """
        A VER entry missing the patch version field cannot produce a complete tuple.

        GIVEN: A VER DataFlash entry where Pat is None
        WHEN: process_ver is called
        THEN: None is returned so the caller tries the MSG fallback
        """
        msg = _make_msg(FWS="ArduCopter V4.6.0", Maj=4, Min=6, Pat=None)
        assert process_ver(msg) is None


# ---------------------------------------------------------------------------
# process_msg_version_fallback
# ---------------------------------------------------------------------------


class TestProcessMsgVersionFallback:
    def test_already_found_version_is_preserved_unchanged(self) -> None:
        """
        Once a version is found from a MSG entry, subsequent MSG entries are ignored.

        GIVEN: A previously parsed version tuple and a new MSG entry with different version
        WHEN: process_msg_version_fallback is called
        THEN: The original tuple is returned unchanged
        """
        existing = ("ArduCopter", 4, 6, 3)
        msg = _make_msg(Message="ArduPlane V4.5.0 (abc)")
        assert process_msg_version_fallback(msg, existing) == existing

    def test_msg_entry_with_full_three_part_version_is_parsed(self) -> None:
        """
        A MSG entry containing a "Vx.y.z" token yields a complete version tuple.

        GIVEN: A MSG DataFlash entry like "ArduCopter V4.6.3 (3fc7011a)"
        WHEN: process_msg_version_fallback is called with no prior result
        THEN: The tuple ("ArduCopter", 4, 6, 3) is returned
        """
        msg = _make_msg(Message="ArduCopter V4.6.3 (3fc7011a)")
        assert process_msg_version_fallback(msg, None) == ("ArduCopter", 4, 6, 3)

    def test_msg_entry_with_two_part_version_defaults_patch_to_zero(self) -> None:
        """
        A MSG entry with only major.minor version defaults patch to 0.

        GIVEN: A MSG DataFlash entry like "ArduPlane V4.5" (no patch component)
        WHEN: process_msg_version_fallback is called with no prior result
        THEN: The tuple ("ArduPlane", 4, 5, 0) is returned with patch=0
        """
        msg = _make_msg(Message="ArduPlane V4.5")
        assert process_msg_version_fallback(msg, None) == ("ArduPlane", 4, 5, 0)

    def test_msg_entry_without_version_token_yields_no_result(self) -> None:
        """
        MSG entries that are not version announcements do not yield a version tuple.

        GIVEN: A MSG DataFlash entry with an unrelated message
        WHEN: process_msg_version_fallback is called
        THEN: None is returned and scanning continues
        """
        msg = _make_msg(Message="Initialising ArduPilot")
        assert process_msg_version_fallback(msg, None) is None

    def test_msg_entry_with_non_numeric_version_yields_no_result(self) -> None:
        """
        Malformed version tokens that cannot be parsed as integers are skipped.

        GIVEN: A MSG DataFlash entry with "Vabc" as the version token
        WHEN: process_msg_version_fallback is called
        THEN: None is returned because the version digits cannot be parsed
        """
        msg = _make_msg(Message="ArduCopter Vabc")
        assert process_msg_version_fallback(msg, None) is None


# ---------------------------------------------------------------------------
# process_param
# ---------------------------------------------------------------------------


class TestProcessParam:
    def test_valid_parm_entry_is_stored_in_both_default_and_current_dicts(self, empty_log_data: LogData) -> None:
        """
        A well-formed PARM log entry populates both default_params and current_params.

        GIVEN: A PARM log entry with a valid name, a Default value, and a Value
        WHEN: process_param is called
        THEN: Both default_params and current_params contain the correct float values
        """
        msg = _make_msg(Name="ATC_RAT_RLL_P", Default=0.135, Value=0.14)
        process_param(msg, empty_log_data)
        assert empty_log_data.default_params["ATC_RAT_RLL_P"] == pytest.approx(0.135)
        assert empty_log_data.current_params["ATC_RAT_RLL_P"] == pytest.approx(0.14)

    def test_repeated_parm_entry_does_not_overwrite_first_occurrence(self, empty_log_data: LogData) -> None:
        """
        Only the first PARM occurrence is kept; periodic repeats in the log are ignored.

        GIVEN: Two PARM entries for the same parameter (as happens in real logs every ~30 s)
        WHEN: process_param is called for both entries
        THEN: Both default_params and current_params retain the values from the first entry
        """
        msg1 = _make_msg(Name="ATC_RAT_RLL_P", Default=0.135, Value=0.14)
        msg2 = _make_msg(Name="ATC_RAT_RLL_P", Default=0.200, Value=0.20)
        process_param(msg1, empty_log_data)
        process_param(msg2, empty_log_data)
        assert empty_log_data.default_params["ATC_RAT_RLL_P"] == pytest.approx(0.135)
        assert empty_log_data.current_params["ATC_RAT_RLL_P"] == pytest.approx(0.14)

    def test_overly_long_param_name_is_silently_skipped(self, empty_log_data: LogData) -> None:
        """
        PARM entries with names longer than 16 characters are discarded with a warning.

        GIVEN: A PARM log entry whose name exceeds PARAM_NAME_MAX_LEN
        WHEN: process_param is called
        THEN: No entry is added to either parameter dict
        """
        msg = _make_msg(Name="A" * 17, Default=1.0, Value=1.0)
        process_param(msg, empty_log_data)
        assert len(empty_log_data.default_params) == 0
        assert len(empty_log_data.current_params) == 0

    def test_malformed_param_name_is_silently_skipped(self, empty_log_data: LogData) -> None:
        """
        PARM entries whose name violates the naming regex are discarded with a warning.

        GIVEN: A PARM log entry with a name starting with a digit
        WHEN: process_param is called
        THEN: No entry is added to either parameter dict
        """
        msg = _make_msg(Name="1INVALID", Default=1.0, Value=1.0)
        process_param(msg, empty_log_data)
        assert len(empty_log_data.default_params) == 0
        assert len(empty_log_data.current_params) == 0

    def test_parm_entry_without_default_value_still_stores_current_value(self, empty_log_data: LogData) -> None:
        """
        When a PARM entry has no Default (older firmware), current_params is still populated.

        GIVEN: A PARM log entry with Default=None and a real Value
        WHEN: process_param is called
        THEN: current_params receives the value but default_params has no entry
        """
        msg = _make_msg(Name="ARMING_CHECK", Default=None, Value=1.0)
        process_param(msg, empty_log_data)
        assert "ARMING_CHECK" not in empty_log_data.default_params
        assert empty_log_data.current_params["ARMING_CHECK"] == pytest.approx(1.0)

    def test_parm_entry_without_any_value_stores_nothing(self, empty_log_data: LogData) -> None:
        """
        A PARM entry with both Default and Value as None contributes nothing to log data.

        GIVEN: A PARM log entry where both Default and Value are None
        WHEN: process_param is called
        THEN: Neither parameter dict is populated
        """
        msg = _make_msg(Name="ARMING_CHECK", Default=None, Value=None)
        process_param(msg, empty_log_data)
        assert len(empty_log_data.default_params) == 0
        assert len(empty_log_data.current_params) == 0

    def test_param_with_no_default_is_not_treated_as_duplicate_on_second_occurrence(self, empty_log_data: LogData) -> None:
        """
        When a param's first occurrence lacks a Default, a later occurrence can still populate default_params.

        GIVEN: First PARM entry has Default=None (only current_params is written, Value=1.0)
               Second PARM entry has a real Default and a different Value
        WHEN: process_param is called for both entries
        THEN: default_params is set from the second entry; current_params retains the first entry's Value
        """
        msg1 = _make_msg(Name="ARMING_CHECK", Default=None, Value=1.0)
        msg2 = _make_msg(Name="ARMING_CHECK", Default=1.0, Value=2.0)
        process_param(msg1, empty_log_data)
        process_param(msg2, empty_log_data)
        # Second entry fills default_params because it was absent
        assert empty_log_data.default_params["ARMING_CHECK"] == pytest.approx(1.0)
        # current_params keeps the first entry's value — the second occurrence must not overwrite it
        assert empty_log_data.current_params["ARMING_CHECK"] == pytest.approx(1.0)

    def test_param_with_no_value_is_not_treated_as_duplicate_on_second_occurrence(self, empty_log_data: LogData) -> None:
        """
        When a param's first occurrence lacks a Value, a later occurrence can still populate current_params.

        GIVEN: First PARM entry has Value=None (only default_params is written, Default=5.0)
               Second PARM entry has a real Value and a different Default
        WHEN: process_param is called for both entries
        THEN: current_params is set from the second entry; default_params retains the first entry's Default
        """
        msg1 = _make_msg(Name="ARMING_CHECK", Default=5.0, Value=None)
        msg2 = _make_msg(Name="ARMING_CHECK", Default=9.0, Value=3.0)
        process_param(msg1, empty_log_data)
        process_param(msg2, empty_log_data)
        # default_params keeps the first entry's value
        assert empty_log_data.default_params["ARMING_CHECK"] == pytest.approx(5.0)
        # Second entry fills current_params because it was absent
        assert empty_log_data.current_params["ARMING_CHECK"] == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# process_bat
# ---------------------------------------------------------------------------


class TestProcessBat:
    def test_bat_entry_populates_all_telemetry_fields(self, bat_msg: MagicMock, empty_log_data: LogData) -> None:
        """
        All numeric fields of a BAT log entry are stored in the battery telemetry.

        GIVEN: A complete BAT log entry for battery instance 0 with known values
        WHEN: process_bat is called
        THEN: All telemetry lists contain exactly the expected values
        """
        process_bat(bat_msg, empty_log_data)
        bat = empty_log_data.batteries[0]
        assert bat.time_us == [1_000_000]
        assert bat.volt == [pytest.approx(16.8)]
        assert bat.volt_r == [pytest.approx(16.5)]
        assert bat.curr == [pytest.approx(10.5)]
        assert bat.curr_tot == [pytest.approx(105.0)]
        assert bat.enrg_tot == [pytest.approx(1764.0)]
        assert bat.temp == [pytest.approx(28.3)]
        assert bat.res == [pytest.approx(0.012)]
        assert bat.rem_pct == [pytest.approx(94.5)]
        assert bat.health == [1]
        assert bat.state_health == [1]

    def test_bat_entry_without_health_fields_defaults_to_zero(self, bat_msg: MagicMock, empty_log_data: LogData) -> None:
        """
        BAT entries from older firmware that lack H/SH fields default those fields to 0.

        GIVEN: A BAT log entry where attributes H and SH are absent (older firmware)
        WHEN: process_bat is called
        THEN: health and state_health are stored as 0, not raising AttributeError
        """
        del bat_msg.H
        del bat_msg.SH
        process_bat(bat_msg, empty_log_data)
        bat = empty_log_data.batteries[0]
        assert bat.health == [0]
        assert bat.state_health == [0]

    def test_multiple_bat_entries_for_same_instance_are_appended(self, bat_msg: MagicMock, empty_log_data: LogData) -> None:
        """
        Successive BAT entries for the same instance build up time-series data.

        GIVEN: Two BAT log entries for battery instance 0 with different voltages
        WHEN: process_bat is called twice
        THEN: The volt list contains both values in order
        """
        second_msg = _make_msg(
            Inst=0,
            TimeUS=2_000_000,
            Volt=16.2,
            VoltR=16.0,
            Curr=11.0,
            CurrTot=116.0,
            EnrgTot=1860.0,
            Temp=29.0,
            Res=0.013,
            RemPct=90.0,
            H=1,
            SH=1,
        )

        process_bat(bat_msg, empty_log_data)
        process_bat(second_msg, empty_log_data)
        bat = empty_log_data.batteries[0]
        assert bat.volt == [pytest.approx(16.8), pytest.approx(16.2)]
        assert len(bat.time_us) == 2

    def test_bat_entries_for_different_instances_are_stored_separately(
        self, bat_msg: MagicMock, empty_log_data: LogData
    ) -> None:
        """
        BAT entries for different battery instances are stored in independent BatteryData objects.

        GIVEN: Two BAT log entries for instances 0 (from fixture) and 1 with a different voltage
        WHEN: process_bat is called for both
        THEN: Each instance has its own entry in the batteries dict with the correct voltage
        """
        # bat_msg is instance 0 (Volt=16.8); build instance 1 with Volt=12.4
        msg1 = _make_msg(
            Inst=1,
            TimeUS=1_000_000,
            Volt=12.4,
            VoltR=12.2,
            Curr=5.0,
            CurrTot=50.0,
            EnrgTot=620.0,
            Temp=27.0,
            Res=0.008,
            RemPct=80.0,
            H=1,
            SH=1,
        )

        process_bat(bat_msg, empty_log_data)
        process_bat(msg1, empty_log_data)
        assert 0 in empty_log_data.batteries
        assert 1 in empty_log_data.batteries
        assert empty_log_data.batteries[0].volt == [pytest.approx(16.8)]
        assert empty_log_data.batteries[1].volt == [pytest.approx(12.4)]


# ---------------------------------------------------------------------------
# process_frame_type
# ---------------------------------------------------------------------------


class TestProcessFrameType:
    def test_frame_type_parameter_is_extracted_from_current_params(self, empty_log_data: LogData) -> None:
        """
        The FRAME_TYPE parameter value is stored on LogData so vehicle geometry is known.

        GIVEN: A LogData whose current_params contains FRAME_TYPE = 1.0 (X-frame quad)
        WHEN: process_frame_type is called
        THEN: log_data.frame_type is set to integer 1
        """
        empty_log_data.current_params["FRAME_TYPE"] = 1.0
        process_frame_type(empty_log_data)
        assert empty_log_data.frame_type == 1

    def test_frame_type_remains_none_when_parameter_is_absent(self, empty_log_data: LogData) -> None:
        """
        Logs from vehicles that never set FRAME_TYPE leave frame_type as None.

        GIVEN: A LogData with no current_params (empty log or pre-parameter log)
        WHEN: process_frame_type is called
        THEN: log_data.frame_type stays None without raising an error
        """
        process_frame_type(empty_log_data)
        assert empty_log_data.frame_type is None


# ---------------------------------------------------------------------------
# extract_log (integration via mocks)
# ---------------------------------------------------------------------------


class TestExtractLog:
    def test_firmware_version_and_parameters_are_extracted_from_log(self, mock_mlog: MagicMock) -> None:
        """
        A typical flight log yields firmware version, default params, and current params.

        GIVEN: A .bin log containing a VER entry and a PARM entry
        WHEN: extract_log is called
        THEN: firmware_info, default_params, current_params, and message counts are populated
        """
        parm_msg = _make_parm_msg("ATC_RAT_RLL_P", 0.135, 0.14)
        ver_msg = _make_ver_msg()
        mock_mlog.recv_match.side_effect = [parm_msg, ver_msg, None]

        with patch(
            "ardupilot_methodic_configurator.log_analysis.backend_log_extraction.open_log",
            return_value=mock_mlog,
        ):
            result = extract_log("dummy.bin")

        assert result.firmware_info == ("ArduCopter", 4, 6, 3)
        assert result.default_params["ATC_RAT_RLL_P"] == pytest.approx(0.135)
        assert result.current_params["ATC_RAT_RLL_P"] == pytest.approx(0.14)
        assert result.messages["PARM"] == 1
        assert result.messages["VER"] == 1
        assert "MSG" not in result.messages

    def test_log_connection_is_always_closed_even_when_parsing_fails(self, mock_mlog: MagicMock) -> None:
        """
        The log file is closed in the finally block so no file handles are leaked.

        GIVEN: A log connection whose recv_match raises an unexpected RuntimeError
        WHEN: extract_log is called
        THEN: RuntimeError propagates to the caller AND the connection is closed exactly once
        """
        mock_mlog.recv_match.side_effect = RuntimeError("unexpected corruption")

        with (
            patch(
                "ardupilot_methodic_configurator.log_analysis.backend_log_extraction.open_log",
                return_value=mock_mlog,
            ),
            pytest.raises(RuntimeError),
        ):
            extract_log("dummy.bin")

        mock_mlog.close.assert_called_once()

    def test_msg_entries_provide_version_when_ver_entry_is_absent(self, mock_mlog: MagicMock) -> None:
        """
        Older firmware logs without VER entries can still yield version via MSG scanning.

        GIVEN: A .bin log containing only a MSG entry with a parseable version string
        WHEN: extract_log is called
        THEN: firmware_info is populated from the MSG fallback
        """
        msg_msg = _make_log_msg("MSG", Message="ArduCopter V4.6.3 (3fc7011a)")
        mock_mlog.recv_match.side_effect = [msg_msg, None]

        with patch(
            "ardupilot_methodic_configurator.log_analysis.backend_log_extraction.open_log",
            return_value=mock_mlog,
        ):
            result = extract_log("dummy.bin")

        assert result.firmware_info == ("ArduCopter", 4, 6, 3)
        assert result.messages["MSG"] == 1
        assert "VER" not in result.messages

    def test_frame_type_is_extracted_and_message_counts_are_complete(self, mock_mlog: MagicMock) -> None:
        """
        FRAME_TYPE from PARM entries is extracted and message counts are always populated.

        GIVEN: A .bin log containing a PARM entry for FRAME_TYPE
        WHEN: extract_log is called
        THEN: frame_type is set to the correct integer and PARM appears in messages
        """
        parm_msg = _make_parm_msg("FRAME_TYPE", 1.0, 1.0)
        mock_mlog.recv_match.side_effect = [parm_msg, None]

        with patch(
            "ardupilot_methodic_configurator.log_analysis.backend_log_extraction.open_log",
            return_value=mock_mlog,
        ):
            result = extract_log("dummy.bin")

        assert result.frame_type == 1
        assert result.messages["PARM"] == 1
        assert "VER" not in result.messages
        assert "MSG" not in result.messages

    def test_bat_entries_are_collected_into_battery_telemetry(self, bat_msg: MagicMock, mock_mlog: MagicMock) -> None:
        """
        BAT log entries are stored in the batteries dict for downstream analysis.

        GIVEN: A .bin log containing a BAT entry for instance 0
        WHEN: extract_log is called
        THEN: batteries dict contains an entry for instance 0 with the correct voltage
        """
        bat_msg.get_type.return_value = "BAT"
        mock_mlog.recv_match.side_effect = [bat_msg, None]

        with patch(
            "ardupilot_methodic_configurator.log_analysis.backend_log_extraction.open_log",
            return_value=mock_mlog,
        ):
            result = extract_log("dummy.bin")

        assert 0 in result.batteries
        assert result.batteries[0].volt == [pytest.approx(16.8)]
        assert result.messages["BAT"] == 1
        assert "PARM" not in result.messages
        assert "VER" not in result.messages
        assert "MSG" not in result.messages

    def test_ver_entry_takes_precedence_over_msg_fallback(self, mock_mlog: MagicMock) -> None:
        """
        VER entries are authoritative; MSG-derived versions are discarded when VER is present.

        GIVEN: A log containing both a MSG version entry and a VER entry with different versions
        WHEN: extract_log is called
        THEN: firmware_info reflects the VER entry, not the MSG entry
        """
        msg_msg = _make_log_msg("MSG", Message="ArduCopter V4.5.0 (oldhash)")
        ver_msg = _make_ver_msg(vehicle="ArduCopter", maj=4, min_=6, pat=3)
        mock_mlog.recv_match.side_effect = [msg_msg, ver_msg, None]

        with patch(
            "ardupilot_methodic_configurator.log_analysis.backend_log_extraction.open_log",
            return_value=mock_mlog,
        ):
            result = extract_log("dummy.bin")

        assert result.firmware_info == ("ArduCopter", 4, 6, 3)
        assert result.messages["MSG"] == 1
        assert result.messages["VER"] == 1

    def test_empty_log_yields_none_firmware_info_and_empty_message_counts(self, mock_mlog: MagicMock) -> None:
        """
        A log file with no messages at all returns a LogData with no firmware info.

        GIVEN: A .bin log that contains no messages (recv_match returns None immediately)
        WHEN: extract_log is called
        THEN: firmware_info is None, messages dict is empty, and no params are stored
        """
        # mock_mlog fixture already sets recv_match.return_value = None
        with patch(
            "ardupilot_methodic_configurator.log_analysis.backend_log_extraction.open_log",
            return_value=mock_mlog,
        ):
            result = extract_log("empty.bin")

        assert result.firmware_info is None
        assert not result.messages
        assert not result.default_params
        assert not result.current_params

    def test_log_with_no_version_entries_yields_none_firmware_info(self, mock_mlog: MagicMock) -> None:
        """
        A log that has PARM entries but no VER or parseable MSG entry has no firmware info.

        GIVEN: A .bin log with only a PARM entry and an unrelated MSG entry
        WHEN: extract_log is called
        THEN: firmware_info is None while parameters are still extracted normally
        """
        parm_msg = _make_parm_msg("ATC_RAT_RLL_P", 0.135, 0.14)
        msg_msg = _make_log_msg("MSG", Message="Initialising ArduPilot")
        mock_mlog.recv_match.side_effect = [parm_msg, msg_msg, None]

        with patch(
            "ardupilot_methodic_configurator.log_analysis.backend_log_extraction.open_log",
            return_value=mock_mlog,
        ):
            result = extract_log("dummy.bin")

        assert result.firmware_info is None
        assert "ATC_RAT_RLL_P" in result.default_params
        assert result.messages["PARM"] == 1
        assert result.messages["MSG"] == 1
