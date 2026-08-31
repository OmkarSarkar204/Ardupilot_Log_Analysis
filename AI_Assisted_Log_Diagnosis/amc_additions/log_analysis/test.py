# # """
# # Full pipeline test: runs analyze_log() (the real entry point AMC uses) across
# # every log you have, prints availability/analysis results only - no JSON report,
# # no schema validation.

# # Run:
# #     python -m ardupilot_methodic_configurator.log_analysis.test
# # """

# # from ardupilot_methodic_configurator.backend_filesystem_vehicle_components import VehicleComponents
# # from ardupilot_methodic_configurator.extract_param_defaults import extract_parameter_values
# # from ardupilot_methodic_configurator.log_analysis.backend_data_sources import load_apm_pdef, load_configuration_steps
# # from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import extract_log
# # from ardupilot_methodic_configurator.log_analysis.data_model_log_analysis import analyze_log
# # from ardupilot_methodic_configurator.log_analysis.data_model_log_analysis_context import LogAnalysisContext

# # LOGFILES = [
# #     "ardupilot_methodic_configurator/log_analysis/4_5_5.bin",
# #     "ardupilot_methodic_configurator/log_analysis/ALT_HOLD.BIN",
# #     "ardupilot_methodic_configurator/log_analysis/altitude_estimation_4.7.bin",
# #     "ardupilot_methodic_configurator/log_analysis/quick_tune_1_only_ALT_HOLD.BIN",
# # ]

# # VEHICLE_DIR = "ardupilot_methodic_configurator/log_analysis"
# # VEHICLE_TYPE = "ArduCopter"


# # def inspect_esc_instance_field(log_data) -> None:  # noqa: ANN001
# #     columns = log_data.get_message_columns("ESC")
# #     if columns is None or columns.size == 0:
# #         print("  No ESC data in this log")
# #         return
# #     names = tuple(columns.dtype.names or ())
# #     if "Instance" not in names:
# #         print("  No 'Instance' field present")
# #         return
# #     instance_values = log_data.get_field("ESC", "Instance", scaled=False)
# #     unique_instances = sorted(set(instance_values.tolist()))
# #     print(f"  Unique Instance values: {unique_instances}")
# #     if "Err" in names:
# #         err_values = log_data.get_field("ESC", "Err")
# #         for inst in unique_instances:
# #             mask = instance_values == inst
# #             print(f"    Instance {inst}: {mask.sum()} records, Err max={err_values[mask].max():.2f}")


# # def inspect_vibe_clip_field(log_data) -> None:  # noqa: ANN001
# #     columns = log_data.get_message_columns("VIBE")
# #     if columns is None or columns.size == 0:
# #         print("  No VIBE data in this log")
# #         return
# #     clip_values = log_data.get_field("VIBE", "Clip", scaled=False)
# #     print(f"  Clip min={clip_values.min()}, max={clip_values.max()}")


# # def print_availability_result(result) -> None:  # noqa: ANN001
# #     print(f"  {result.name}: {result.state} available={result.available}")
# #     if result.issues:
# #         for issue in result.issues:
# #             print(f"    - {issue.message} [{issue.config_step or '(no step)'}]")


# # def print_analysis_result(result) -> None:  # noqa: ANN001
# #     print(f"  {result.name}: {len(result.outcomes)} outcome(s)")
# #     for finding in result.outcomes:
# #         ts = f"{finding.timestamp_us / 1e6:.1f}s" if finding.timestamp_us is not None else "static"
# #         val = f"{finding.value:.3f}" if finding.value is not None else "-"
# #         param = f" [param={finding.param_name}]" if finding.param_name else ""
# #         suggested = f" [suggested={finding.suggested_value:.2f}]" if finding.suggested_value is not None else ""
# #         step = f" [step={finding.related_step!r}]" if finding.related_step is not None else " [step=None]"
# #         print(f"    - [{ts}] {finding.message}")
# #         print(f"          value={val}{param}{suggested}{step}")


# # def print_dshot_params(params: dict) -> None:
# #     loop_rate = params.get("SCHED_LOOP_RATE")
# #     dshot_rate = params.get("SERVO_DSHOT_RATE")
# #     spin_arm = params.get("MOT_SPIN_ARM")
# #     spin_min = params.get("MOT_SPIN_MIN")
# #     print(f"  SCHED_LOOP_RATE={loop_rate}  SERVO_DSHOT_RATE={dshot_rate}")
# #     print(f"  MOT_SPIN_ARM={spin_arm}  MOT_SPIN_MIN={spin_min}")


# # def run_one_log(logfile: str, vehicle_components: dict) -> None:
# #     print("=" * 70)
# #     print(logfile)
# #     print("=" * 70)

# #     try:
# #         log_data = extract_log(logfile)
# #         params = extract_parameter_values(logfile, "values")
# #     except (OSError, ValueError) as error:
# #         print(f"  FAILED TO LOAD: {error}")
# #         return

# #     apm_doc = load_apm_pdef(VEHICLE_DIR, VEHICLE_TYPE)
# #     configuration_steps = load_configuration_steps(VEHICLE_TYPE) or {}

# #     print_dshot_params(params)

# #     context = LogAnalysisContext(
# #         parameters=params,
# #         configuration_steps=configuration_steps,
# #         apm_doc=apm_doc,
# #         vehicle_components=vehicle_components,
# #     )

# #     summary = analyze_log(log_data, context)

# #     print(f"availability_results: {len(summary.availability_results)}")
# #     for result in summary.availability_results:
# #         print_availability_result(result)

# #     print()
# #     print(f"analysis_results: {len(summary.analysis_results)}")
# #     for result in summary.analysis_results:
# #         print_analysis_result(result)

# #     print()
# #     print("--- ESC raw field inspection ---")
# #     inspect_esc_instance_field(log_data)

# #     print()
# #     print("--- VIBE raw field inspection ---")
# #     inspect_vibe_clip_field(log_data)

# #     print()


# # def main() -> None:
# #     vehicle_components_fs = VehicleComponents()
# #     vehicle_components_fs.load_vehicle_components_json_data(VEHICLE_DIR)
# #     vehicle_components = (vehicle_components_fs.vehicle_components_fs.data or {}).get("Components", {})

# #     print(f"vehicle_components loaded: {bool(vehicle_components)}")
# #     if vehicle_components:
# #         print(f"  keys: {list(vehicle_components.keys())}")
# #     print()

# #     for logfile in LOGFILES:
# #         run_one_log(logfile, vehicle_components)


# # if __name__ == "__main__":
# #     main()

# """
# Single-log test: builds the enriched report (step_info/param_info embedded)
# and validates it against log_analysis_schema.json.

# Run:
#     python -m ardupilot_methodic_configurator.log_analysis.test_single
# """

# import json
# from pathlib import Path

# from ardupilot_methodic_configurator.backend_filesystem_vehicle_components import VehicleComponents
# from ardupilot_methodic_configurator.extract_param_defaults import extract_parameter_values
# from ardupilot_methodic_configurator.log_analysis.backend_data_sources import load_apm_pdef, load_configuration_steps
# from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import extract_log
# from ardupilot_methodic_configurator.log_analysis.data_model_log_analysis import analyze_log
# from ardupilot_methodic_configurator.log_analysis.data_model_log_analysis_context import LogAnalysisContext
# from ardupilot_methodic_configurator.log_analysis.backend_log_analysis_report_generator import build_report, write_report

# LOGFILE = "ardupilot_methodic_configurator/log_analysis/quick_tune_1_only_ALT_HOLD.BIN"
# VEHICLE_DIR = "ardupilot_methodic_configurator/log_analysis"
# VEHICLE_TYPE = "ArduCopter"
# SCHEMA_FILE = Path("ardupilot_methodic_configurator/log_analysis/log_analysis_schema.json")


# def main() -> None:
#     vehicle_components_fs = VehicleComponents()
#     vehicle_components_fs.load_vehicle_components_json_data(VEHICLE_DIR)
#     full_vehicle_components_file = vehicle_components_fs.vehicle_components_fs.data or {}
#     flat_vehicle_components = full_vehicle_components_file.get("Components", {})

#     log_data = extract_log(LOGFILE)
#     params = extract_parameter_values(LOGFILE, "values")
#     apm_doc = load_apm_pdef(VEHICLE_DIR, VEHICLE_TYPE)
#     configuration_steps = load_configuration_steps(VEHICLE_TYPE) or {}

#     # Sanity check the raw apm_doc shape for one real param before trusting build_param_info's assumptions
#     print("=== apm_doc['MOT_SPIN_MIN'] raw shape ===")
#     print(json.dumps(apm_doc.get("MOT_SPIN_MIN", {}), indent=2, default=str))
#     print()

#     context = LogAnalysisContext(
#         parameters=params,
#         configuration_steps=configuration_steps,
#         apm_doc=apm_doc,
#         vehicle_components=flat_vehicle_components,
#     )

#     summary = analyze_log(log_data, context)

#     report = build_report(summary, log_data, full_vehicle_components_file, configuration_steps, apm_doc)
#     report_path = write_report(VEHICLE_DIR, report)
#     print(f"Report written to {report_path}")
#     print()

#     # Print one enriched finding in full, to eyeball step_info/param_info by hand
#     print("=== Sample enriched finding (first outcome with a param_name, if any) ===")
#     for entry in report["analysis"]:
#         if entry.get("status") != "completed":
#             continue
#         for outcome in entry.get("outcomes", []):
#             if outcome.get("param_name"):
#                 print(json.dumps(outcome, indent=2, default=str))
#                 break
#         else:
#             continue
#         break
#     print()

#     if SCHEMA_FILE.exists():
#         from jsonschema import Draft202012Validator
#         from jsonschema.validators import RefResolver

#         with open(SCHEMA_FILE, encoding="utf-8") as f:
#             schema = json.load(f)

#         resolver_base_dir = SCHEMA_FILE.parent.parent
#         resolver = RefResolver(base_uri=f"{resolver_base_dir.resolve().as_uri()}/", referrer=schema)
#         validator = Draft202012Validator(schema, resolver=resolver)
#         errors = sorted(validator.iter_errors(report), key=str)

#         print("=== schema validation ===")
#         if not errors:
#             print("PASSED")
#         else:
#             print(f"FAILED - {len(errors)} error(s):")
#             for error in errors:
#                 print(f"  - {error.message} (at {list(error.path)})")
#     else:
#         print(f"Schema file not found at {SCHEMA_FILE}")


# if __name__ == "__main__":
#     main()


"""
Standalone demo: runs the full log analysis pipeline, shows results in a
minimal Tkinter window, and generates an AI summary on button click.

Runs independently of the main AMC app - just a quick way to see the whole
pipeline (extract -> analyze -> report -> LLM) working end to end.

Run:
    python -m ardupilot_methodic_configurator.log_analysis.test_llm_frontend
"""

import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

from ardupilot_methodic_configurator.backend_filesystem_vehicle_components import VehicleComponents
from ardupilot_methodic_configurator.extract_param_defaults import extract_parameter_values
from ardupilot_methodic_configurator.log_analysis.backend_data_sources import load_apm_pdef, load_configuration_steps
from ardupilot_methodic_configurator.log_analysis.backend_log_analysis_report_generator import build_report, write_report
from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import extract_log
from ardupilot_methodic_configurator.log_analysis.data_model_log_analysis import analyze_log
from ardupilot_methodic_configurator.log_analysis.data_model_log_analysis_context import LogAnalysisContext
from ardupilot_methodic_configurator.log_analysis.log_analyse_llm import ChatSession

LOGFILE = "ardupilot_methodic_configurator/log_analysis/4_5_4.bin"
VEHICLE_DIR = "ardupilot_methodic_configurator/log_analysis"
VEHICLE_TYPE = "ArduCopter"


def run_pipeline() -> dict:
    """Run extract -> analyze -> build_report, return the report dict."""
    log_data = extract_log(LOGFILE)
    parameters = extract_parameter_values(LOGFILE, "values")
    apm_doc = load_apm_pdef(VEHICLE_DIR, VEHICLE_TYPE)
    configuration_steps = load_configuration_steps(VEHICLE_TYPE) or {}

    vehicle_components_fs = VehicleComponents()
    vehicle_components_fs.load_vehicle_components_json_data(VEHICLE_DIR)
    vehicle_components_full = vehicle_components_fs.vehicle_components_fs.data or {}
    vehicle_components = vehicle_components_full.get("Components", {})

    context = LogAnalysisContext(
        parameters=parameters,
        configuration_steps=configuration_steps,
        apm_doc=apm_doc,
        vehicle_components=vehicle_components,
    )

    summary = analyze_log(log_data, context)
    report = build_report(summary, log_data, vehicle_components_full, configuration_steps, apm_doc, LOGFILE)
    write_report(VEHICLE_DIR, report)
    return report


class LogAnalysisDemoWindow:
    """Minimal standalone window showing pipeline results and an on-demand AI summary."""

    def __init__(self, root: tk.Tk, report: dict) -> None:
        self.root = root
        self.report = report
        self.chat_session: ChatSession | None = None
        self.root.title("Log Analysis Demo")
        self.root.geometry("800x600")

        self._build_widgets()
        self._populate_results()

    def _build_widgets(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        results_frame = ttk.Frame(notebook)
        notebook.add(results_frame, text="Availability + Analysis")
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap="word")
        self.results_text.pack(fill="both", expand=True)

        chat_frame = ttk.Frame(notebook)
        notebook.add(chat_frame, text="Ask the AI")

        self.chat_transcript = scrolledtext.ScrolledText(chat_frame, wrap="word", state="disabled")
        self.chat_transcript.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        input_row = ttk.Frame(chat_frame)
        input_row.pack(fill="x", padx=8, pady=(0, 8))

        self.chat_entry = ttk.Entry(input_row)
        self.chat_entry.pack(side="left", fill="x", expand=True)
        self.chat_entry.bind("<Return>", lambda _event: self._on_send_clicked())

        self.chat_send_button = ttk.Button(input_row, text="Send", command=self._on_send_clicked)
        self.chat_send_button.pack(side="left", padx=(4, 0))

    def _append_chat_line(self, speaker: str, text: str) -> None:
        self.chat_transcript.configure(state="normal")
        self.chat_transcript.insert("end", f"{speaker}: {text}\n\n")
        self.chat_transcript.configure(state="disabled")
        self.chat_transcript.see("end")

    def _populate_results(self) -> None:
        lines = []
        lines.append("=== DATA QUALITY ===\n")
        for result in self.report["data_availability"]:
            lines.append(f"[{result['state'].upper()}] {result['name']}: {result['reason']}")
            for issue in result.get("issues", []):
                lines.append(f"    - {issue['message']}")
        lines.append("\n=== ANALYSIS ===\n")
        for entry in self.report["analysis"]:
            if entry["status"] == "pending":
                lines.append(f"[PENDING] {entry['name']}")
                continue
            lines.append(f"[COMPLETED] {entry['name']}: {entry['reason']}")
            for outcome in entry.get("outcomes", []):
                lines.append(f"    - {outcome['message']}")

        self.results_text.insert("1.0", "\n".join(lines))
        self.results_text.configure(state="disabled")

    def _on_send_clicked(self) -> None:
        question = self.chat_entry.get().strip()
        if not question:
            return

        self.chat_entry.delete(0, "end")
        self._append_chat_line("You", question)
        self.chat_send_button.configure(state="disabled")

        if self.chat_session is None:
            self._append_chat_line("System", "Loading model and grounding it in this report, this may take a minute...")

        thread = threading.Thread(target=self._chat_worker, args=(question,), daemon=True)
        thread.start()

    def _chat_worker(self, question: str) -> None:
        try:
            if self.chat_session is None:
                self.chat_session = ChatSession(self.report)
            answer = self.chat_session.ask(question)
            error_text = None
        except Exception as error:  # pylint: disable=broad-except
            answer = None
            error_text = str(error)

        # Hand results back to the main thread - never touch tkinter widgets
        # directly from a background thread.
        self.root.after(0, self._on_answer_ready, answer, error_text)

    def _on_answer_ready(self, answer: str | None, error_text: str | None) -> None:
        self.chat_send_button.configure(state="normal")
        if error_text is not None:
            self._append_chat_line("Error", error_text)
            return
        self._append_chat_line("AI", answer or "(empty response)")


def main() -> None:
    print("Running pipeline...")
    report = run_pipeline()
    print(f"Pipeline done. {len(report['data_availability'])} availability results, {len(report['analysis'])} analysis entries.")

    root = tk.Tk()
    LogAnalysisDemoWindow(root, report)
    root.mainloop()


if __name__ == "__main__":
    main()