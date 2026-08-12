"""
Log quality report window for the ArduPilot Methodic Configurator.

Displays a parsed ArduPilot .bin log analysis.

This file is part of ArduPilot Methodic Configurator. https://github.com/ArduPilot/MethodicConfigurator

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

import tkinter as tk
import webbrowser
from tkinter import ttk

from ardupilot_methodic_configurator import _
from ardupilot_methodic_configurator.frontend_tkinter_base_window import BaseWindow
from ardupilot_methodic_configurator.frontend_tkinter_scroll_frame import ScrollFrame
from ardupilot_methodic_configurator.frontend_tkinter_show import show_tooltip
from ardupilot_methodic_configurator.log_analysis.backend_log_analysis import LogSummary
from ardupilot_methodic_configurator.log_analysis.backend_log_quality_check import StepValidationResult
from ardupilot_methodic_configurator.log_analysis.backend_vehicle_overview import (
    AirspeedInfo,
    BaroInfo,
    CompassInfo,
    ImuInfo,
)
from ardupilot_methodic_configurator.log_analysis.data_model_quality_base import LogQualityResult


class LogQualityReportWindow(BaseWindow):
    """Displays log analysis results as a beginner-friendly, detailed dashboard."""

    def __init__(self, root_tk: tk.Tk | tk.Toplevel, summary: LogSummary) -> None:
        super().__init__(root_tk)
        self.summary = summary
        self.root.title(_("Log Quality Report"))
        self.root.geometry(self.calculate_scaled_geometry(1000, 750))
        self.center_window(self.root, root_tk)
        self.root.resizable(width=True, height=True)

        self._build_header_summary()
        self._build_stats_cards()
        self._build_tabs()

    @staticmethod
    def _clean_devtype(name: str | None) -> str:
        """Strip DEVTYPE_ prefix and category prefix from device type names."""
        if not name or name == "Unknown":
            return "-"
        for prefix in ("DEVTYPE_INS_", "DEVTYPE_BARO_", "DEVTYPE_AIRSPEED_", "DEVTYPE_"):
            if name.startswith(prefix):
                return name[len(prefix) :]
        return name

    @staticmethod
    def _fmt_val(val: object) -> str:
        """Format values to replace None, 'Unknown', or 'None' strings with a dash."""
        if val is None:
            return "-"
        s = str(val)
        if s in ("Unknown", "None", ""):
            return "-"
        return s

    @staticmethod
    def _fmt_duration(sec: float | None) -> str:
        if sec is None:
            return "-"
        m = int(sec) // 60
        s = int(sec) % 60
        return f"{m}m {s}s"

    @staticmethod
    def _fmt_filesize(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _build_header_summary(self) -> None:
        """A quick TL;DR banner for beginners."""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(side=tk.TOP, fill=tk.X, padx=14, pady=(14, 6))

        issues_count = sum(len(res.issues) for res in self.summary.quality_results)
        failed_steps = sum(1 for res in self.summary.step_results if not res.valid)
        total_problems = issues_count + failed_steps

        if total_problems == 0:
            status_text = _("Status: Log looks healthy. No major issues detected.")
            status_color = "#2e7d32"
        else:
            status_text = _("Status: Found %s potential issue(s) to review.") % total_problems
            status_color = "#d84315"

        ttk.Label(
            header_frame,
            text=status_text,
            foreground=status_color,
            font=("TkDefaultFont", 13, "bold"),
        ).pack(side=tk.LEFT)

    def _build_stats_cards(self) -> None:
        """Groups stats into distinct visual cards."""
        card_container = ttk.Frame(self.main_frame)
        card_container.pack(side=tk.TOP, fill=tk.X, padx=12, pady=8)

        vehicle_card = ttk.LabelFrame(card_container, text=_("Vehicle & Firmware"))
        vehicle_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        hw = self.summary.hardware_report
        v = hw.vehicle if hw else None
        fc = v.flight_controller if v and v.flight_controller else "-"
        board = hw.board_name if hw and hw.board_name else "-"

        if v and v.vehicle_type and v.major is not None:
            firmware_base = f"{v.vehicle_type} {v.major}.{v.minor}.{v.patch}"
            short_type = v.vehicle_type.replace("Ardu", "")
            version_str = f"{short_type}-{v.major}.{v.minor}.{v.patch}"
            release_url = f"https://github.com/ArduPilot/ardupilot/tree/{version_str}"
            self._add_clickable_key_value(vehicle_card, "Firmware:", f"{firmware_base} ({version_str})", release_url)
        else:
            self._add_key_value(vehicle_card, "Firmware:", "-")

        self._add_key_value(vehicle_card, "FC:", fc)
        self._add_key_value(vehicle_card, "Board:", board)

        flight_card = ttk.LabelFrame(card_container, text=_("Log Overview"))
        flight_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)

        self._add_key_value(flight_card, "Flight Time:", self._fmt_duration(self.summary.flight_duration_sec))
        self._add_key_value(flight_card, "Log Size:", self._fmt_filesize(self.summary.file_size_bytes))
        self._add_key_value(flight_card, "Total Msgs:", str(self.summary.total_messages))

        perf_card = ttk.LabelFrame(card_container, text=_("System Performance"))
        perf_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        pm = self.summary.pm_status
        self._add_key_value(perf_card, "Avg CPU:", f"{pm.average_cpu_load:.1f}%" if pm else "-")
        self._add_key_value(perf_card, "Peak CPU:", f"{pm.peak_cpu_load:.1f}%" if pm else "-")
        self._add_key_value(perf_card, "Long Loops:", str(pm.scheduler_long_loops) if pm else "-")

    def _add_key_value(self, parent: ttk.Frame, key: str, value: str) -> None:
        """Helper to cleanly pack key-value pairs inside cards."""
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, padx=10, pady=3)
        ttk.Label(row, text=key, foreground="#555555", font=("TkDefaultFont", 11), width=14).pack(side=tk.LEFT)
        ttk.Label(row, text=value, font=("TkDefaultFont", 11, "bold")).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _add_clickable_key_value(self, parent: ttk.Frame, key: str, value: str, url: str) -> None:
        """Helper for links with webbrowser support."""
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, padx=10, pady=3)
        ttk.Label(row, text=key, foreground="#555555", font=("TkDefaultFont", 11), width=14).pack(side=tk.LEFT)

        link_label = ttk.Label(
            row,
            text=value,
            foreground="#0055ff",
            cursor="hand2",
            font=("TkDefaultFont", 11, "bold", "underline"),
        )
        link_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        link_label.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))
        show_tooltip(link_label, _("Open release page on GitHub"))

    def _build_tabs(self) -> None:
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=("TkDefaultFont", 11))

        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=(12, 12))

        quality_frame = ttk.Frame(notebook)
        notebook.add(quality_frame, text=_("  Quality Report  "))
        self._build_quality_tab(quality_frame)

        hardware_frame = ttk.Frame(notebook)
        notebook.add(hardware_frame, text=_("  Hardware Overview  "))
        self._build_hardware_tab(hardware_frame)

    def _build_quality_tab(self, parent: ttk.Frame) -> None:
        """Splits quality results into Needs Attention and Passed Checks."""
        scroll_container = ScrollFrame(parent)
        scroll_container.pack(fill=tk.BOTH, expand=True)
        inner = scroll_container.view_port

        needs_attention = []
        passed_checks = []

        for q_res in self.summary.quality_results:
            if q_res.state != "info":
                needs_attention.append(("quality", q_res))
            else:
                passed_checks.append(("quality", q_res))

        for s_res in self.summary.step_results:
            if not s_res.valid:
                needs_attention.append(("step", s_res))
            else:
                passed_checks.append(("step", s_res))

        if needs_attention:
            ttk.Label(
                inner,
                text=_("Requires Attention"),
                font=("TkDefaultFont", 14, "bold"),
                foreground="#d84315",
            ).pack(anchor=tk.W, padx=14, pady=(18, 6))

            for item_type, item in needs_attention:
                if item_type == "quality":
                    self._quality_result_card(inner, item)
                else:
                    self._step_result_card(inner, item)

            ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=14, pady=(14, 14))

        if passed_checks:
            ttk.Label(
                inner,
                text=_("Passed Checks"),
                font=("TkDefaultFont", 14, "bold"),
                foreground="#2e7d32",
            ).pack(anchor=tk.W, padx=14, pady=(10, 6))

            for item_type, item in passed_checks:
                if item_type == "quality":
                    self._quality_result_card(inner, item)
                else:
                    self._step_result_card(inner, item)

    def _quality_result_card(self, parent: ttk.Frame, result: LogQualityResult) -> None:
        card = ttk.Frame(parent)
        card.pack(fill=tk.X, padx=14, pady=6)

        tag = "OK" if result.state == "info" else "WARN"
        color = "#2e7d32" if result.state == "info" else "#d32f2f"

        icon_lbl = ttk.Label(card, text=tag, foreground=color, font=("TkDefaultFont", 12, "bold"), width=8)
        icon_lbl.pack(side=tk.LEFT)

        text_frame = ttk.Frame(card)
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(text_frame, text=result.name, font=("TkDefaultFont", 12, "bold")).pack(anchor=tk.W)

        reason_lbl = ttk.Label(
            text_frame,
            text=result.reason,
            foreground="#444444",
            font=("TkDefaultFont", 11),
            wraplength=500,
        )
        reason_lbl.pack(anchor=tk.W, fill=tk.X)
        text_frame.bind(
            "<Configure>",
            lambda e, label_ref=reason_lbl: label_ref.configure(wraplength=max(10, e.width - 15)),
        )

        if result.issues:
            issues_text = f"{len(result.issues)} Issue(s)"
            tooltip = "\n".join(f"- {i.message}" for i in result.issues)
            issue_lbl = ttk.Label(card, text=issues_text, foreground="#d84315", font=("TkDefaultFont", 11, "bold"))
            issue_lbl.pack(side=tk.RIGHT, padx=14)

            show_tooltip(issue_lbl, tooltip)
            show_tooltip(icon_lbl, tooltip)
            show_tooltip(card, tooltip)

    def _step_result_card(self, parent: ttk.Frame, result: StepValidationResult) -> None:
        card = ttk.Frame(parent)
        card.pack(fill=tk.X, padx=14, pady=6)

        tag = "PASS" if result.valid else "FAIL"
        color = "#2e7d32" if result.valid else "#d84315"

        icon_lbl = ttk.Label(card, text=tag, foreground=color, font=("TkDefaultFont", 12, "bold"), width=8)
        icon_lbl.pack(side=tk.LEFT)

        display_name = result.name or result.step
        lbl = ttk.Label(card, text=display_name, font=("TkDefaultFont", 12), wraplength=500)
        lbl.pack(side=tk.LEFT, anchor=tk.W, fill=tk.X, expand=True)
        card.bind(
            "<Configure>",
            lambda e, label_ref=lbl: label_ref.configure(wraplength=max(10, e.width - 90)),
        )

        if not result.valid:
            issues_lines = [issue for msg_result in result.message_results.values() for issue in msg_result.issues]
            if issues_lines:
                tooltip = "\n".join(f"- {i}" for i in issues_lines)
                show_tooltip(icon_lbl, tooltip)
                show_tooltip(lbl, tooltip)
                show_tooltip(card, tooltip)

    def _build_hardware_tab(self, parent: ttk.Frame) -> None:
        hw = self.summary.hardware_report
        if hw is None:
            ttk.Label(
                parent,
                text=_("No hardware data available"),
                font=("TkDefaultFont", 11),
                foreground="gray",
            ).pack(padx=24, pady=24)
            return

        scroll_container = ScrollFrame(parent)
        scroll_container.pack(fill=tk.BOTH, expand=True)
        inner = scroll_container.view_port

        if hw.imus:
            self._build_imu_cards(inner, hw.imus)

        if hw.compasses:
            self._build_compass_cards(inner, hw.compasses)

        if hw.baros:
            self._build_baro_cards(inner, hw.baros)

        if hw.airspeed_sensors:
            self._build_airspeed_cards(inner, hw.airspeed_sensors)

    def _build_imu_cards(self, parent: ttk.Frame, imus: list[ImuInfo]) -> None:
        ttk.Label(parent, text=_("IMUs"), font=("TkDefaultFont", 13, "bold")).pack(anchor=tk.W, padx=14, pady=(16, 6))
        for imu in imus:
            card = ttk.LabelFrame(parent, text=f"IMU {imu.instance}")
            card.pack(side=tk.TOP, fill=tk.X, padx=14, pady=6)

            col1 = ttk.Frame(card)
            col1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)
            col2 = ttk.Frame(card)
            col2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)

            self._add_key_value(col1, "Accel:", self._clean_devtype(imu.accel_name))
            self._add_key_value(col1, "Gyro:", self._clean_devtype(imu.gyro_name))
            self._add_key_value(col1, "Bus Type:", self._fmt_val(imu.accel_bus_type))
            self._add_key_value(col1, "Accel Healthy:", self._fmt_val(imu.accel_healthy))

            self._add_key_value(col2, "Accel Calibrated:", self._fmt_val(imu.accel_calibrated))
            self._add_key_value(col2, "Gyro Calibrated:", self._fmt_val(imu.gyro_calibrated))
            self._add_key_value(col2, "Temp Calibrated:", self._fmt_val(imu.accel_temp_calibrated))
            self._add_key_value(col2, "Gyro Healthy:", self._fmt_val(imu.gyro_healthy))

    def _build_compass_cards(self, parent: ttk.Frame, compasses: list[CompassInfo]) -> None:
        ttk.Label(parent, text=_("Compasses"), font=("TkDefaultFont", 13, "bold")).pack(anchor=tk.W, padx=14, pady=(18, 6))
        for compass in compasses:
            card = ttk.LabelFrame(parent, text=f"Compass {compass.instance}")
            card.pack(side=tk.TOP, fill=tk.X, padx=14, pady=6)

            col1 = ttk.Frame(card)
            col1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)
            col2 = ttk.Frame(card)
            col2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)

            self._add_key_value(col1, "Chip:", self._clean_devtype(compass.name))
            self._add_key_value(col1, "Bus Type:", self._clean_devtype(compass.bus_type))
            self._add_key_value(col1, "External:", self._fmt_val(compass.external))

            self._add_key_value(col2, "Calibrated:", self._fmt_val(compass.calibrated))
            self._add_key_value(col2, "Motor Calibrated:", self._fmt_val(compass.motor_calibrated))
            self._add_key_value(col2, "Healthy:", self._fmt_val(compass.healthy))

    def _build_baro_cards(self, parent: ttk.Frame, baros: list[BaroInfo]) -> None:
        ttk.Label(parent, text=_("Barometers"), font=("TkDefaultFont", 13, "bold")).pack(anchor=tk.W, padx=14, pady=(18, 6))
        for baro in baros:
            card = ttk.LabelFrame(parent, text=f"Baro {baro.instance}")
            card.pack(side=tk.TOP, fill=tk.X, padx=14, pady=6)

            col1 = ttk.Frame(card)
            col1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)
            col2 = ttk.Frame(card)
            col2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)

            self._add_key_value(col1, "Chip:", self._clean_devtype(baro.name))
            self._add_key_value(col1, "Bus Type:", self._clean_devtype(baro.bus_type))

            self._add_key_value(col2, "Wind Comp.:", self._fmt_val(baro.wind_compensation))
            self._add_key_value(col2, "Healthy:", self._fmt_val(baro.healthy))

    def _build_airspeed_cards(self, parent: ttk.Frame, airspeeds: list[AirspeedInfo]) -> None:
        ttk.Label(
            parent,
            text=_("Airspeed Sensors"),
            font=("TkDefaultFont", 13, "bold"),
        ).pack(anchor=tk.W, padx=14, pady=(18, 6))

        for arspd in airspeeds:
            card = ttk.LabelFrame(parent, text=f"Airspeed {arspd.instance}")
            card.pack(side=tk.TOP, fill=tk.X, padx=14, pady=6)

            col1 = ttk.Frame(card)
            col1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=4)

            self._add_key_value(col1, "Type:", self._fmt_val(arspd.sensor_type))
            self._add_key_value(col1, "In Use:", self._fmt_val(arspd.use))
            self._add_key_value(col1, "Healthy:", self._fmt_val(arspd.healthy))

    def run(self) -> None:
        self.root.mainloop()