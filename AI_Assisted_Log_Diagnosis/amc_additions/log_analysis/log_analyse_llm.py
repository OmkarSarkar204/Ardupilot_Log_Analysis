"""
Minimal LLM integration for log analysis reports.

This file is part of ArduPilot Methodic Configurator. https://github.com/ArduPilot/MethodicConfigurator

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-FileCopyrightText: 2026 Omkar Sarkar <omkarsarkar24@gmail.com>

Model: Qwen2.5-3B-Instruct, Q4_K_M GGUF, downloaded once and cached locally. Apache 2.0 licensed.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import json
from pathlib import Path
from typing import Any

MODEL_REPO = "Qwen/Qwen2.5-3B-Instruct-GGUF"
MODEL_FILENAME = "qwen2.5-3b-instruct-q4_k_m.gguf"
MODEL_CACHE_DIR = Path.home() / ".cache" / "ardupilot_methodic_configurator" / "models"

SYSTEM_PROMPT = (
    "You are a flight log analysis assistant for ArduPilot drones. You are given a "
    "structured JSON payload containing flight timing, data quality results, and analysis "
    "findings from a single flight log. It does NOT include the vehicle's hardware inventory - "
    "never describe or discuss hardware components, their brand, firmware, or specifications, "
    "since none of that information is present in what you were given.\n\n"
    "Base every claim about 'what is working well' or 'what needs attention' ONLY on entries "
    "inside 'outcomes' arrays in the 'analysis' section. The 'data_quality' section only "
    "confirms whether enough data existed to run analysis - it is not itself a finding; never "
    "present a data_quality entry's 'reason' (like 'data present and good for analysis') as if "
    "it were an analysis result or evidence that a subsystem is 'working well'.\n\n"
    "Before answering, review every 'outcomes' entry for the relevant subsystem(s) - only state "
    "that a parameter or subsystem is fine if no outcome entry contradicts that. Never state two "
    "contradictory claims about the same parameter.\n\n"
    "An analysis entry with status 'pending' means that subsystem was NOT analyzed. State "
    "plainly, using its 'reason' field, why it could not be analyzed. Never invent a 'pending' "
    "status for a subsystem that is not actually marked pending in the payload.\n\n"
    "Each finding may include step_info (why a configuration step matters, with links) and "
    "param_info (parameter documentation, range, units) - use these to ground your explanation. "
    "Include any available wiki_url or blog_url directly in your answer when discussing that finding.\n\n"
    "Always write in plain conversational sentences and paragraphs. Never use markdown syntax: "
    "no '#' headers, no '**' bold, no '-' or '*' bullet lists.\n\n"
    "Answer the pilot's specific question directly and concisely, using only information from "
    "the payload you were given. If it does not contain enough information to answer, say so "
    "plainly rather than guessing."
)

_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "vibrat": ("Vibration", "IMU"),
    "jitter": ("Vibration", "IMU"),
    "jitery": ("Vibration", "IMU"),
    "shak": ("Vibration", "IMU"),
    "oscillat": ("Vibration", "IMU"),
    "wobbl": ("Vibration", "IMU"),
    "unstable": ("Vibration", "IMU", "ESC"),
    "stability": ("Vibration", "IMU", "ESC"),
    "battery": ("Battery",),
    "volt": ("Battery",),
    "current": ("Battery", "ESC"),
    "capacity": ("Battery",),
    "power": ("Battery",),
    "esc": ("ESC",),
    "motor": ("ESC",),
    "spin": ("ESC",),
    "dshot": ("ESC", "IMU"),
    "rpm": ("ESC",),
    "gps": ("GPS",),
    "satellite": ("GPS",),
    "hdop": ("GPS",),
    "imu": ("IMU",),
    "temperature": ("IMU",),
    "calibrat": ("IMU",),
    "notch": ("IMU", "ESC"),
    "error": ("ERR",),
    "performance": ("System Performance", "PM"),
    "cpu": ("System Performance", "PM"),
    "loop": ("System Performance", "PM"),
}


def _strip_to_llm_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": report.get("schema_version"),
        "flight": report.get("flight"),
        "data_quality": report.get("data_quality", []),
        "analysis": report.get("analysis", []),
    }


def _select_relevant_sections(payload: dict[str, Any], question: str) -> dict[str, Any]:
    question_lower = question.lower()
    matched_topics: set[str] = set()
    for keyword, topics in _TOPIC_KEYWORDS.items():
        if keyword in question_lower:
            matched_topics.update(topics)

    if not matched_topics:
        return payload

    def _name_matches(name: str) -> bool:
        return any(topic.lower() in name.lower() for topic in matched_topics)

    filtered = dict(payload)
    filtered["data_quality"] = [entry for entry in payload.get("data_quality", []) if _name_matches(entry.get("name", ""))]
    filtered["analysis"] = [entry for entry in payload.get("analysis", []) if _name_matches(entry.get("name", ""))]

    if not filtered["data_quality"] and not filtered["analysis"]:
        return payload

    return filtered


def _download_model_if_needed() -> Path:
    """Download the GGUF model to a local cache directory if it isn't already there."""
    model_path = MODEL_CACHE_DIR / MODEL_FILENAME
    if model_path.exists():
        return model_path

    from huggingface_hub import hf_hub_download  # noqa: PLC0415 - optional dependency, imported lazily

    MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    downloaded_path = hf_hub_download(
        repo_id=MODEL_REPO,
        filename=MODEL_FILENAME,
        local_dir=str(MODEL_CACHE_DIR),
    )
    return Path(downloaded_path)


def _load_model() -> Any:  # noqa: ANN401
    """Load the GGUF model via llama-cpp-python. Raises a clear error if the dependency is missing."""
    try:
        from llama_cpp import Llama  # noqa: PLC0415 - optional dependency, imported lazily
    except ImportError as error:
        msg = "llama-cpp-python is required for LLM summaries. Install with: pip install llama-cpp-python"
        raise RuntimeError(msg) from error

    model_path = _download_model_if_needed()
    return Llama(
        model_path=str(model_path),
        n_ctx=8192,
        n_threads=8,  # adjust to your machine's real core count if needed
        verbose=False,
    )


def _serialize(payload: dict[str, Any], max_chars: int = 6000) -> str:
    serialized = json.dumps(payload, indent=2)
    return serialized[:max_chars]


_cached_model: Any = None


def _get_model() -> Any:  # noqa: ANN401
    """Load the model once and reuse it across calls - loading is the slow part, not inference."""
    global _cached_model  # noqa: PLW0603
    if _cached_model is None:
        _cached_model = _load_model()
    return _cached_model


class ChatSession:
    """
    Answers questions about one log analysis report.

    Each call to .ask() is a fully independent, stateless completion: system
    prompt + only the payload sections relevant to that specific question,
    with no accumulated conversation history and no hardware inventory.
    """

    def __init__(self, report: dict[str, Any]) -> None:
        self.payload = _strip_to_llm_payload(report)

    def ask(self, question: str) -> str:
        """Answer a single question, grounded only in the payload sections relevant to it."""
        model = _get_model()
        relevant = _select_relevant_sections(self.payload, question)
        payload_text = _serialize(relevant)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Here is the relevant data:\n\n{payload_text}\n\nQuestion: {question}",
            },
        ]
        response = model.create_chat_completion(messages=messages, max_tokens=320, temperature=0.2)
        return response["choices"][0]["message"]["content"]


def summarize_report(report: dict[str, Any]) -> str:
    """Generate a plain-language summary of the full log analysis report using the local model."""
    model = _get_model()
    payload_text = _serialize(_strip_to_llm_payload(report), max_chars=10000)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Here is the full report data:\n\n{payload_text}\n\nSummarize it for the pilot."},
    ]

    response = model.create_chat_completion(messages=messages, max_tokens=500, temperature=0.2)
    return response["choices"][0]["message"]["content"]


def summarize_report_file(report_path: str) -> str:
    """Load a log_analysis_report.json file and summarize it."""
    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)
    return summarize_report(report)
