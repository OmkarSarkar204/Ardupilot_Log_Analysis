"""
Base Quality model for all base classes and combined results.

Defines the common result data model and the base class used by all subsystem quality analysis models.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

from dataclasses import dataclass
from typing import Any

from ardupilot_methodic_configurator import _
from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import LogData
from ardupilot_methodic_configurator.log_analysis.backend_log_quality_check import (
    find_step_for_message,
    find_step_for_parameter,
)


@dataclass
class QualityIssue:
    """One detected issue, paired with the configuration step that would fix it."""

    message: str
    config_step: str = ""


@dataclass
class LogQualityResult:
    """Result produced by a subsystem quality model (battery, GPS, etc.)."""

    available: bool
    state: str
    reason: str
    issues: list[QualityIssue]
    name: str


class BaseLogQualityAnalysisModel:
    """Base class for log analysis models."""

    LOG_BIT = 0

    def __init__(
        self,
        log_data: LogData,
        parameters: dict[str, float],
        configuration_steps: dict[str, Any],
        vehicle_components: dict[str, Any] | None = None,
    ) -> None:
        self.log_data = log_data
        self.parameters = parameters or {}
        self.vehicle_components = vehicle_components or {}
        self.configuration_steps = configuration_steps

    def step_for_parameter(self, param_name: str) -> str:
        return find_step_for_parameter(self.configuration_steps, param_name) or ""

    def build_result(self, issues: list[QualityIssue], name: str) -> LogQualityResult:
        return LogQualityResult(
            available=True,
            state="info" if not issues else "warning",
            reason=_("{name} data present and good for analysis").format(name=name)
            if not issues else _("{name} data has quality issues").format(name=name),
            issues=issues,
            name=name,
        )
