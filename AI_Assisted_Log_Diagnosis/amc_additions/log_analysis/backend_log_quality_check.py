"""
ArduPilot log quality checker.

Validates that the messages and params required by the Methodic Configurator configuration
steps are present, also checks if a specific analysis can be performed and the logged records match their FMT schema.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

from dataclasses import dataclass, field
from json import JSONDecodeError
from json import load as json_load
from logging import error as logging_error
from os import path as os_path
from typing import Any

from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import LogData, MessageSchema


def load_configuration_steps() -> dict[str, Any]:
    """Load the Methodic Configurator configuration steps from 'configuration_steps_ArduCopter.json'."""
    config_file = os_path.join(
        os_path.dirname(os_path.dirname(os_path.abspath(__file__))),
        "configuration_steps_ArduCopter.json",
    )

    try:
        with open(config_file, encoding="utf-8") as file:
            return json_load(file)
    except FileNotFoundError:
        logging_error("Configuration file '%s' not found", config_file)
    except JSONDecodeError as e:
        logging_error("Error in configuration file '%s': %s", config_file, e)

    return {}


CONFIGURATION_STEPS = load_configuration_steps()


@dataclass
class MessageValidation:
    """Validation result for a single message type and its schema."""

    valid: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class StepValidationResult:
    """Validation result for configuration step."""

    step: str
    name: str
    valid: bool
    message_results: dict[str, MessageValidation]


class LogQualityChecker:
    """Checks whether a log contains the required messages for each configuration step."""

    def validate_fmt_schema(self, schema: MessageSchema, records: list[dict]) -> MessageValidation:
        """
        Validate one message schema.

        Args:
            schema: Schema extracted from the FMT messages.
            records: Decoded records for this message type.

        Returns:
            MessageValidation

        """
        issues: list[str] = []

        # To be removed if these checks become stale, as pymavlink should handle these
        if not schema.fields:
            issues.append("Missing field definitions")
        if not schema.format:
            issues.append("Missing format string")
        if schema.length <= 0:
            issues.append("Invalid message length")
        if schema.units and len(schema.units) != len(schema.fields):
            issues.append("Unit count mismatch")
        if schema.multipliers and len(schema.multipliers) != len(schema.fields):
            issues.append("Multiplier count mismatch")

        if not records:
            issues.append(f"{schema.name} has no logging data")
        else:
            record = records[0]
            actual_fields = [field for field in record.keys() if field != "mavpackettype"]  # noqa: SIM118
            expected_fields = list(schema.fields)
            if expected_fields != actual_fields:
                issues.append(f"Field mismatch. Expected {expected_fields}, got {actual_fields}")

        return MessageValidation(
            valid=not issues,
            issues=issues,
        )

    def validate_configuration_steps(self, log_data: LogData) -> list[StepValidationResult]:
        """
        Validate the messages required by the configuration steps.

        Args:
            log_data: Parsed log.

        Returns:
            List of validation results.

        """
        results: list[StepValidationResult] = []

        for step_name, step in CONFIGURATION_STEPS["steps"].items():
            related_messages = step.get("related_bin_messages")
            if not related_messages:
                continue

            step_valid = True
            message_results: dict[str, MessageValidation] = {}

            for message_name, message_info in related_messages.items():
                required = message_info.get("required", False)

                schema = log_data.schemas.get(message_name)

                if schema is None:
                    validation = MessageValidation(
                        valid=False,
                        issues=["Schema not found"],
                    )

                    if required:
                        step_valid = False

                    message_results[message_name] = validation
                    continue

                records = log_data.raw_messages.get(message_name, [])

                validation = self.validate_fmt_schema(
                    schema=schema,
                    records=records,
                )

                if required and not validation.valid:
                    step_valid = False

                message_results[message_name] = validation

            results.append(
                StepValidationResult(
                    step=step_name,
                    name=step.get("blog_text", step_name),
                    valid=step_valid,
                    message_results=message_results,
                )
            )

        return results
