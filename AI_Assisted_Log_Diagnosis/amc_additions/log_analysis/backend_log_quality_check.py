"""
ArduPilot log quality checker.

Validates that the messages required by each analysis plugin, and configuration are present,
and that logged record matches its FMT schema.

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


def load_analysis_plugins() -> dict[str, Any]:
    """Load the analysis plugin from JSON."""
    plugin_file = os_path.join(
        os_path.dirname(os_path.abspath(__file__)),
        "analysis_plugins.json",
    )
    try:
        with open(plugin_file, encoding="utf-8") as file:
            return json_load(file)
    except FileNotFoundError:
        logging_error("Analysis plugins '%s' not found", plugin_file)
    except JSONDecodeError as e:
        logging_error("Error in analysis plugins '%s': %s", plugin_file, e)
    return {}


ANALYSIS_PLUGINS = load_analysis_plugins()


@dataclass
class MessageValidation:
    """Validation result for a single message type and its schema."""

    valid: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class PluginValidationResult:
    """Validation result for one analysis plugin (analysis_plugins.json)."""

    plugin: str
    name: str
    valid: bool
    message_results: dict[str, MessageValidation]


class LogQualityChecker:
    """Checks whether a log is suitable for each analysis plugin."""

    def validate_fmt_schema(self, schema: MessageSchema, records: list[dict]) -> MessageValidation:
        """
        Validate one message schema.

        Args:
            schema: Schema extracted from the FMT messages.
            records: Decoded records for this message type.

        Returns:
            MessageValidation

        """
        # Store the issues iteratively
        issues: list[str] = []

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

    def validate_fmt_plugins(self, log_data: LogData) -> list[PluginValidationResult]:
        """
        Validate every analysis plugin.

        Args:
            log_data: Parsed log.

        Returns:
            List of plugin validation results.

        """
        results: list[PluginValidationResult] = []

        for plugin_name, plugin in ANALYSIS_PLUGINS.items():
            plugin_valid = True
            message_results: dict[str, MessageValidation] = {}

            for message_name in plugin["required_messages"]:
                schema = log_data.schemas.get(message_name)

                if schema is None:
                    plugin_valid = False
                    message_results[message_name] = MessageValidation(
                        valid=False,
                        issues=["Schema not found"],
                    )
                    continue

                records = log_data.raw_messages.get(message_name, [])

                validation = self.validate_fmt_schema(
                    schema=schema,
                    records=records,
                )

                if not validation.valid:
                    plugin_valid = False

                message_results[message_name] = validation

            results.append(
                PluginValidationResult(
                    plugin=plugin_name,
                    name=plugin["name"],
                    valid=plugin_valid,
                    message_results=message_results,
                )
            )

        return results
