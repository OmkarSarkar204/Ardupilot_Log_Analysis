"""
Data model for battery quality check.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""


from ardupilot_methodic_configurator import _
from ardupilot_methodic_configurator.log_analysis.data_model_quality_base import LogQualityResult
from ardupilot_methodic_configurator.log_analysis.data_model_quality_base import BaseLogQualityAnalysisModel



class BatteryLogQualityModel(BaseLogQualityAnalysisModel):
    """Checks battery telemetry and configuration quality."""

    NAME = "Battery"
    CONFIG_STEP = "10_battery_monitor.param"
    # Battery Monitor logging is bit 9 (2^9) in LOG_BITMASK
    LOG_BIT = 512

    def check(self) -> LogQualityResult:
        """
        Run all battery quality checks.

        Returns:
            Battery quality class instance.

        """
        records = self.log_data.get_message_columns("BAT")

        if records is None or len(records) == 0:
            return self._diagnose_absence()

        issues: list[str] = []
        for check in (self.check_voltage, self.check_curr_total, self.check_current, self.check_efficiency):
            issues += check()
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
            config_step=self.CONFIG_STEP,
            issues=issues,
        )

    def check_voltage(self) -> list[str]:
        """
        Validate logged battery voltage values.

        Checks for missing voltage, zero voltage and parameter based voltage defects.

        Returns:
            List of detected issues.

        """
        issues: list[str] = []
        volts = self.log_data.get_field("BAT", "Volt")

        if len(volts) == 0:
            issues.append(_("Voltage values missing from BAT records"))
            return issues

        if volts.max() == 0:
            issues.append(_("Voltage is zero throughout, sensor may not be reading"))

        v_max = self.parameters.get("MOT_BAT_VOLT_MAX")
        v_min = self.parameters.get("MOT_BAT_VOLT_MIN")
        if v_max is not None and v_max > 0 and volts.max() >= 1.2 * v_max:
            issues.append(_("Voltage spike, or MOT_BAT_VOLT_MAX misconfigured"))
        if v_min is not None and v_min > 0 and volts.min() <= 0.8 * v_min:
            issues.append(_("Voltage sag, or MOT_BAT_VOLT_MIN misconfigured"))

        return issues

    def check_current(self) -> list[str]:
        """
        Validate logged battery current values.

        Args:
            records: BAT message records.

        Returns:
            List of detected issues.

        """
        issues: list[str] = []
        current = self.log_data.get_field("BAT", "Curr")
        if len(current) == 0:
            issues.append(_("Current values missing from BAT records"))
        return issues

    def check_curr_total(self) -> list[str]:
        """
        Validate accumulated battery consumption values.

        Returns:
            List of detected issues.

        """
        issues: list[str] = []
        cur_tot = self.log_data.get_field("BAT", "CurrTot")
        if len(cur_tot) == 0:
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

    def check_efficiency(self) -> list[str]:
        issues = []

        frame = self.vehicle_components.get("Frame", {})
        specs = frame.get("Specifications", {})
        tow = specs.get("TOW max Kg", None)
        if tow is None or tow<=0:
            return issues

        volts = self.log_data.get_field("BAT", "Volt")
        curr = self.log_data.get_field("BAT", "Curr")
        if len(volts) == 0 or len(curr) == 0:
            return issues

        avg_pow = volts.mean() * curr.mean()
        efficiency = avg_pow/tow

        if efficiency < 200 or efficiency > 500:
            issues.append(_("Power efficiency out of range, check current vehicle setup"))
        return issues
