"""
Data model for battery quality check.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

from dataclasses import dataclass
from typing import Any

from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import LogData
from ardupilot_methodic_configurator import _


CONFIG_STEP = "10_battery_monitor.param"


@dataclass
class LogBatteryQuality:
    """Battery quality result."""

    available: bool
    state: str
    reason: str
    config_step: str
    issues: list[str]


class BatteryLogQualityModel:
    """Checks battery telemetry and configuration quality."""

    def __init__(self, log_data: LogData, parameters: dict[str, float] | None = None) -> None:
        """
        Initialise the battery quality model.

        Args:
          log_data: Parsed data from log.
          parameters: Extracted parameter values from log.

        """
        self.log_data = log_data
        self.parameters = parameters or {}

    def extract(self, records, field: str) -> list:
        """Extract non empty values from a BAT field."""
        return [r.get(field) for r in records if r.get(field) is not None]

    def build_result(self, issues: list[str]) -> LogBatteryQuality:
        """
        Build the battery quality result.

        Args:
            issues: Detected battery quality issues.

        Returns:
            Battery quality class instance.

        """
        return LogBatteryQuality(
            available=True,
            state="info" if not issues else "warning",
            reason=_("Battery data present and good for analysis") if not issues else _("Battery data has quality issues"),
            config_step="" if not issues else CONFIG_STEP,
            issues=issues,
        )

    def check(self) -> LogBatteryQuality:
        """
        Run all battery quality checks.

        Returns:
            Battery quality class instance.

        """
        records = self.log_data.raw_messages.get("BAT", [])

        if not records:
            return LogBatteryQuality(
                available=False,
                state="warning",
                reason=_("Battery telemetry (BAT) is not logged."),
                config_step=CONFIG_STEP,
                issues=[_("No BAT messages found in log")],
            )

        issues: list[str] = []
        for check in (self.check_voltage, self.check_curr_total, self.check_current):
            issues += check(records)
        issues += self.check_parameters()
        return self.build_result(issues)

    def check_voltage(self, records: Any) -> list[str]:  # noqa: ANN401
        """
        Validate logged battery voltage values.

        Checks for missing voltage, zero voltage and
        parameter based voltage defects.

        Args:
            records: BAT message records.

        Returns:
            List of detected issues.

        """
        issues = []
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
        issues = []
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
        issues = []
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
        issues = []
        monitor = self.parameters.get("BATT_MONITOR")

        if monitor is None:
            return issues

        if monitor == 0:
            issues.append(_("Battery monitoring disabled"))
            return issues

        if self.parameters.get("BATT_LOW_VOLT") == 0:
            issues.append(_("Battery low-voltage failsafe threshold disabled"))
        if self.parameters.get("BATT_CRT_VOLT") == 0:
            issues.append(_("Battery critical-voltage failsafe threshold disabled"))

        return issues
