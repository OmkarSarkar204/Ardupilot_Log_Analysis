"""
Builds a report matching log_analysis_report_schema.json from a LogSummary.

This file is part of ArduPilot Methodic Configurator. https://github.com/ArduPilot/MethodicConfigurator

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-FileCopyrightText: 2026 Omkar Sarkar <omkarsarkar24@gmail.com>

SPDX-License-Identifier: GPL-3.0-or-later
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ardupilot_methodic_configurator.log_analysis.data_model_log_analysis import AVAILABILITY_AND_ANALYSIS_MODELS, LogSummary
from ardupilot_methodic_configurator.log_analysis.data_model_log_data import LogData

SCHEMA_VERSION = 1

_TIMELINE_MESSAGE_CANDIDATES = ("IMU", "BAT", "GPS", "MODE", "VIBE")


def _flight_timeline(log_data: LogData) -> dict[str, float]:
    """Determine start/end/duration in raw microseconds from whichever message is available first."""
    for message_name in _TIMELINE_MESSAGE_CANDIDATES:
        columns = log_data.get_message_columns(message_name)
        if columns is None or columns.size == 0:
            continue
        names = columns.dtype.names or ()
        if "TimeUS" not in names:
            continue
        time_us = log_data.get_field(message_name, "TimeUS", scaled=False)
        if len(time_us) == 0:
            continue
        start = float(time_us.min())
        end = float(time_us.max())
        return {"start_time_us": start, "end_time_us": end, "duration_us": max(0.0, end - start)}

    return {"start_time_us": 0.0, "end_time_us": 0.0, "duration_us": 0.0}


def build_step_info(configuration_steps: dict[str, Any], step_filename: str | None) -> dict[str, Any] | None:
    """Build embeddable step documentation for a related_step/config_step reference."""
    if not step_filename or step_filename not in configuration_steps:
        return None
    step = configuration_steps[step_filename]
    return {
        "why": step.get("why"),
        "why_now": step.get("why_now"),
        "blog_text": step.get("blog_text"),
        "blog_url": step.get("blog_url"),
        "wiki_text": step.get("wiki_text"),
        "wiki_url": step.get("wiki_url"),
    }


def build_param_info(apm_doc: dict[str, Any] | None, param_name: str | None) -> dict[str, Any] | None:
    """Build embeddable parameter metadata for a param_name reference."""
    if not param_name or apm_doc is None or param_name not in apm_doc:
        return None
    info = apm_doc[param_name]
    doc = info.get("documentation")
    doc_text = " ".join(doc) if isinstance(doc, list) else doc
    fields = info.get("fields", {}) if isinstance(info.get("fields"), dict) else {}
    return {
        "human_name": info.get("humanName"),
        "documentation": doc_text,
        "range": fields.get("Range"),
        "units": fields.get("Units"),
    }


def _enrich_issue(issue: dict[str, Any], configuration_steps: dict[str, Any], apm_doc: dict[str, Any] | None) -> dict[str, Any]:
    issue["step_info"] = build_step_info(configuration_steps, issue.get("config_step"))
    issue["param_info"] = build_param_info(apm_doc, issue.get("param_name"))
    return issue


def _enrich_availability_result(
    result_dict: dict[str, Any], configuration_steps: dict[str, Any], apm_doc: dict[str, Any] | None
) -> dict[str, Any]:
    result_dict["issues"] = [
        _enrich_issue(issue, configuration_steps, apm_doc) for issue in result_dict.get("issues", [])
    ]
    return result_dict


def _enrich_outcome(
    outcome: dict[str, Any], configuration_steps: dict[str, Any], apm_doc: dict[str, Any] | None
) -> dict[str, Any]:
    outcome["step_info"] = build_step_info(configuration_steps, outcome.get("related_step"))
    outcome["param_info"] = build_param_info(apm_doc, outcome.get("param_name"))
    return outcome


def _analysis_entries(
    summary: LogSummary, configuration_steps: dict[str, Any], apm_doc: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """
    Build completed/pending analysis entries from summary.availability_results/analysis_results.

    ASSUMPTION being relied on: analyze_log() appends availability_results in
    AVAILABILITY_AND_ANALYSIS_MODELS order, with at most one extra "System Performance"
    entry prepended (from PM validation) that is not part of the registry. That
    offset is detected below and asserted, so this fails loudly instead of
    silently mismatching if analyze_log's ordering ever changes.
    """
    offset = len(summary.availability_results) - len(AVAILABILITY_AND_ANALYSIS_MODELS)
    if offset not in (0, 1):
        msg = (
            f"Unexpected availability_results length ({len(summary.availability_results)}) vs "
            f"AVAILABILITY_AND_ANALYSIS_MODELS length ({len(AVAILABILITY_AND_ANALYSIS_MODELS)}); "
            "the offset assumption in _analysis_entries no longer holds, fix this mapping."
        )
        raise AssertionError(msg)

    analysis_iter = iter(summary.analysis_results)
    entries: list[dict[str, Any]] = []

    for i, (_availability_cls, analysis_cls) in enumerate(AVAILABILITY_AND_ANALYSIS_MODELS):
        if analysis_cls is None:
            continue

        availability_result = summary.availability_results[i + offset]

        if availability_result.available:
            analysis_result = next(analysis_iter)
            entry = {**asdict(analysis_result), "status": "completed"}
            entry["outcomes"] = [
                _enrich_outcome(outcome, configuration_steps, apm_doc) for outcome in entry.get("outcomes", [])
            ]
            entries.append(entry)
        else:
            entries.append({
                "name": f"{availability_result.name} Analysis",
                "status": "pending",
                "reason": availability_result.reason,
                "issues": [issue.message for issue in availability_result.issues],
            })

    return entries


def build_report(
    summary: LogSummary,
    log_data: LogData,
    vehicle_components: dict[str, Any],
    configuration_steps: dict[str, Any],
    apm_doc: dict[str, Any] | None,
    log_filename: str,
) -> dict[str, Any]:
    """Assemble the schema-conformant report from an already-computed LogSummary."""
    return {
        "schema_version": SCHEMA_VERSION,
        "log_file": log_filename,
        "flight": _flight_timeline(log_data),
        "vehicle_components": vehicle_components,
        "data_availability": [
            _enrich_availability_result(asdict(result), configuration_steps, apm_doc) for result in summary.availability_results
        ],
        "analysis": _analysis_entries(summary, configuration_steps, apm_doc),
    }


def write_report(vehicle_dir: str, report: dict[str, Any], filename: str = "log_analysis_report.json") -> Path:
    """Overwrite vehicle_dir's report file with the given report."""
    report_path = Path(vehicle_dir) / filename
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report_path