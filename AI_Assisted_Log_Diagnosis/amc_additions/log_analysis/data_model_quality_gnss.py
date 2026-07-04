"""
Data model for GPS/GNSS quality check.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

from typing import Any

from ardupilot_methodic_configurator import _
from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import LogData, LogQualityResult

CONFIG_STEP = "12_gnss.param"


class GPSLogQualityModel:
    """Checks GPS/GNSS telemetry and configuration quality."""

    NAME = "gps"
    # GPS logging is bit 2 (2^2) in LOG_BITMASK
    LOG_BIT = 4

    def __init__(self, log_data: LogData, parameters: dict[str, float] | None = None) -> None:
        """
        Initialise the GPS quality model.

        Args:
            log_data: Parsed data from log.
            parameters: Extracted parameter values from log.

        """
        self.log_data = log_data
        self.parameters = parameters or {}

    def extract(self, records: Any, field: str) -> list:  # noqa: ANN401
        """Extract non empty values from a GPS field."""
        return [r.get(field) for r in records if r.get(field) is not None]

    def build_result(self, issues: list[str]) -> LogQualityResult:
        """
        Build the GPS/GNSS quality result.

        Args:
            issues: Detected GPS quality issues.

        Returns:
            GPS/GNSS quality class instance.

        """
        return LogQualityResult(
            available=True,
            state="info" if not issues else "warning",
            reason=_("GPS data present and good for analysis") if not issues else _("GPS data has quality issues"),
            config_step="" if not issues else CONFIG_STEP,
            issues=issues,
        )

    def check(self) -> LogQualityResult:
        """
        Run all GPS quality checks.

        Returns:
            GPS quality class instance.

        """
        records = self.log_data.raw_messages.get("GPS", [])

        if not records:
            return self._diagnose_absence()

        issues: list[str] = []
        for check in (self.check_status,):
            issues += check(records)
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
            config_step=CONFIG_STEP,
            issues=issues,
        )

    def check_status(self, records: Any) -> list[str]:  # noqa: ANN401
        """
        Validate GPS fix status.

        Args:
            records: GPS message records.

        Returns:
            List of detected issues.

        """
        issues: list[str] = []
        status = self.extract(records, "Status")
        if not status:
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
