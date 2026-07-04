"""
Data model for battery quality check.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

from typing import Any

from ardupilot_methodic_configurator import _
from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import LogData, LogQualityResult

CONFIG_STEP = "10_battery_monitor.param"


class BatteryLogQualityModel:
    """Checks battery telemetry and configuration quality."""

    NAME = "battery"
    # Battery Monitor logging is bit 9 (2^9) in LOG_BITMASK
    LOG_BIT = 512

    def __init__(self, log_data: LogData, parameters: dict[str, float] | None = None) -> None:
        """
        Initialise the battery quality model.

        Args:
            log_data: Parsed data from log.
            parameters: Extracted parameter values from log.

        """
        self.log_data = log_data
        self.parameters = parameters or {}

    def extract(self, records: Any, field: str) -> list:  # noqa: ANN401
        """Extract non empty values from a BAT field."""
        return [r.get(field) for r in records if r.get(field) is not None]

    def build_result(self, issues: list[str]) -> LogQualityResult:
        """
        Build the battery quality result.

        Args:
            issues: Detected battery quality issues.

        Returns:
            Battery quality class instance.

        """
        return LogQualityResult(
            available=True,
            state="info" if not issues else "warning",
            reason=_("Battery data present and good for analysis") if not issues else _("Battery data has quality issues"),
            config_step="" if not issues else CONFIG_STEP,
            issues=issues,
        )

    def check(self) -> LogQualityResult:
        """
        Run all battery quality checks.

        Returns:
            Battery quality class instance.

        """
        records = self.log_data.raw_messages.get("BAT", [])

        if not records:
            return self._diagnose_absence()

        issues: list[str] = []
        for check in (self.check_voltage, self.check_curr_total, self.check_current):
            issues += check(records)
        issues += self.check_parameters()
        return self.build_result(issues)

    def _diagnose_absence(self) -> LogQualityResult:
        """Diagnose why BAT data is absent using LOG_BITMASK."""
        bitmask = self.parameters.get("LOG_BITMASK")
        monitor = self.parameters.get("BATT_MONITOR")
        if bitmask is not None and (int(bitmask) & self.LOG_BIT) == 0:
          reason = _("Battery logging is disabled in LOG_BITMASK")
          issues = [_("Enable battery logging (LOG_BITMASK bit) to record BAT data")]
        elif monitor == 0:
          reason = _("Battery logging enabled but BATT_MONITOR is 0 (monitor disabled)")
          issues = [_("Set BATT_MONITOR to enable the battery monitor")]
        else:
          reason = _("Battery logging enabled but no data, monitor may not be configured properly")
          issues = [_("No BAT messages found")]


        return LogQualityResult(
            available=False,
            state="warning",
            reason=reason,
            config_step=CONFIG_STEP,
            issues=issues,
        )

    def check_voltage(self, records: Any) -> list[str]:  # noqa: ANN401
        """
        Validate logged battery voltage values.

        Checks for missing voltage, zero voltage and parameter based voltage defects.

        Args:
            records: BAT message records.

        Returns:
            List of detected issues.

        """
        issues: list[str] = []
        volts = self.extract(records, "Volt")

        if not volts:
            issues.append(_("Voltage values missing from BAT records"))
            return issues

        if max(volts) == 0:
            issues.append(_("Voltage is zero throughout, sensor may not be reading"))

        v_max = self.parameters.get("MOT_BAT_VOLT_MAX")
        v_min = self.parameters.get("MOT_BAT_VOLT_MIN")
        if v_max is not None and v_max > 0 and max(volts) >= 1.2 * v_max:
            issues.append(_("Voltage spike, or MOT_BAT_VOLT_MAX misconfigured"))
        if v_min is not None and v_min > 0 and min(volts) <= 0.8 * v_min:
            issues.append(_("Voltage sag, or MOT_BAT_VOLT_MIN misconfigured"))

        return issues

    def check_current(self, records: Any) -> list[str]:  # noqa: ANN401
        """
        Validate logged battery current values.

        Args:
            records: BAT message records.

        Returns:
            List of detected issues.

        """
        issues: list[str] = []
        current = self.extract(records, "Curr")
        if not current:
            issues.append(_("Current values missing from BAT records"))
        return issues

    def check_curr_total(self, records: Any) -> list[str]:  # noqa: ANN401
        """
        Validate accumulated battery consumption values.

        Args:
            records: BAT message records.

        Returns:
            List of detected issues.

        """
        issues: list[str] = []
        cur_tot = self.extract(records, "CurrTot")
        if not cur_tot:
            issues.append(_("CurrTot missing from BAT records"))
        return issues

    def check_parameters(self) -> list[str]:
        """
        Validate battery-related parameter configuration.

        Returns:
            List of detected parameter issues.

        """
        issues: list[str] = []
        monitor = self.parameters.get("BATT_MONITOR")

        if monitor is None:
            return issues

        if self.parameters.get("BATT_LOW_VOLT") == 0:
            issues.append(_("Battery low-voltage failsafe threshold disabled"))
        if self.parameters.get("BATT_CRT_VOLT") == 0:
            issues.append(_("Battery critical-voltage failsafe threshold disabled"))

        return issues
