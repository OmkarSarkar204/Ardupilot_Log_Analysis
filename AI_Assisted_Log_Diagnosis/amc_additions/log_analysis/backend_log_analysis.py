"""
ArduPilot log analysis manager.

Coordinates log metadata extraction, quality validation, and subsystem quality
analysis into a single summary object for the Methodic Configurator frontend.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

from dataclasses import dataclass
from typing import Any

from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import LogData
from ardupilot_methodic_configurator.log_analysis.data_model_quality_base import LogQualityResult
from ardupilot_methodic_configurator.log_analysis.data_model_quality_battery import BatteryLogQualityModel
from ardupilot_methodic_configurator.log_analysis.data_model_quality_gnss import GPSLogQualityModel
from ardupilot_methodic_configurator.log_analysis.backend_log_quality_check import (
    PMStatus,
    StepValidationResult,
    MessageValidation,
    get_pm_status,
    validate_configuration_steps,
)

QUALITY_MODELS = [BatteryLogQualityModel, GPSLogQualityModel]

@dataclass
class LogSummary:
    """Summary of a parsed ArduPilot log."""

    flight_duration_sec: float
    file_size_bytes: int
    total_messages: int
    message_types: int
    parameter_count: int
    pm_status: PMStatus | None
    quality_results: list[LogQualityResult]
    step_results: list[StepValidationResult]


def analyze_log(
    log_data: LogData,
    parameters: dict[str, float],
    vehicle_components: dict[str, Any] | None = None,
) -> LogSummary:
    """
    Run all log quality analyses and return a summary suitable for the frontend.

    Args:
        log_data: Parsed log.
        parameters: Vehicle parameters extracted from the log.
        vehicle_components: Optional vehicle component database.

    Returns:
        Complete log analysis summary.

    """
    if vehicle_components is None:
        vehicle_components = {}

    pm_status = get_pm_status(log_data)

    quality_results: list[LogQualityResult] = [
        model(log_data, parameters, vehicle_components).check()
        for model in QUALITY_MODELS
    ]

    step_results = validate_configuration_steps(log_data, vehicle_type="ArduCopter")

    return LogSummary(
        flight_duration_sec=log_data.flight_duration_sec,
        file_size_bytes=log_data.log_file_size,
        total_messages=sum(log_data.msg_count.values()),
        message_types=len(log_data.schemas),
        parameter_count=len(parameters),
        pm_status=pm_status,
        quality_results=quality_results,
        step_results=step_results,
    )
