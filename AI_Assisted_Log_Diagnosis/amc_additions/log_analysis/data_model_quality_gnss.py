"""
Data model for GPS/GNSS quality check.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""


from ardupilot_methodic_configurator import _
from ardupilot_methodic_configurator.log_analysis.data_model_quality_base import LogQualityResult
from ardupilot_methodic_configurator.log_analysis.data_model_quality_base import BaseLogQualityAnalysisModel




class GPSLogQualityModel(BaseLogQualityAnalysisModel):
    """Checks GPS/GNSS telemetry and configuration quality."""

    NAME = "GPS"
    CONFIG_STEP = "12_gnss.param"
    # GPS logging is bit 2 (2^2) in LOG_BITMASK
    LOG_BIT = 4

    def check(self) -> LogQualityResult:
        """
        Run all GPS quality checks.

        Returns:
            GPS quality class instance.

        """
        records = self.log_data.get_message_columns("GPS")

        if records is None or len(records) == 0:
            return self._diagnose_absence()

        issues: list[str] = []
        for check in (self.check_status,):
            issues += check()
        issues += self.check_parameters()
        return self.build_result(issues)

    def _diagnose_absence(self) -> LogQualityResult:
        """Diagnose why GPS data is absent using LOG_BITMASK."""
        bitmask = self.parameters.get("LOG_BITMASK")
        if bitmask is not None and (int(bitmask) & self.LOG_BIT) == 0:
            reason = _("GPS logging is disabled in LOG_BITMASK")
            issues = [_("Enable GPS logging (LOG_BITMASK bit) to record GPS data")]
        else:
            reason = _("GPS/GNSS telemetry not logged but logging enabled; check the GPS physical connection")
            issues = [_("No GPS messages found")]
        return LogQualityResult(
            available=False,
            state="warning",
            reason=reason,
            config_step=self.CONFIG_STEP,
            issues=issues,
        )

    def check_status(self) -> list[str]:
        """
        Validate GPS fix status.

        Args:
            records: GPS message records.

        Returns:
            List of detected issues.

        """
        issues: list[str] = []
        status = self.log_data.get_field("GPS", "Status")
        if len(status) == 0:
            issues.append(_("GPS fix status missing from GPS records"))
        elif max(status) < 3:
            issues.append(_("GPS never achieved a 3D fix"))
        return issues

    def check_parameters(self) -> list[str]:
        """
        Validate GPS-related parameter configuration.

        Returns:
            List of detected parameter issues.

        """
        issues: list[str] = []
        gps_type = self.parameters.get("GPS_TYPE", self.parameters.get("GPS1_TYPE"))
        if gps_type == 0:
            issues.append(_("GPS type not configured (set to None)"))
        return issues

# TODO: need to remove the hardcoing like batt and gps in both the data models and also remove the step number for the json file :(