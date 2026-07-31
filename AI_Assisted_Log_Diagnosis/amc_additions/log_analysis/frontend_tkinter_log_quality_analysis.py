"""
Log quality report window for the ArduPilot Methodic Configurator.

Displays a parsed ArduPilot .bin log analysis as a structured report card:
- Stats strip (flight time, CPU, memory, log metadata)
- Vehicle strip (firmware, board, FC identity)
- Tabbed content: Quality checks | Hardware report

This file is part of ArduPilot Methodic Configurator. https://github.com/ArduPilot/MethodicConfigurator

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

import tkinter as tk
from tkinter import ttk
import webbrowser

from ardupilot_methodic_configurator import _
from ardupilot_methodic_configurator.frontend_tkinter_base_window import BaseWindow
from ardupilot_methodic_configurator.frontend_tkinter_show import show_tooltip
from ardupilot_methodic_configurator.log_analysis.backend_log_analysis import LogSummary
from ardupilot_methodic_configurator.log_analysis.backend_log_quality_check import StepValidationResult
from ardupilot_methodic_configurator.log_analysis.data_model_quality_base import LogQualityResult
from ardupilot_methodic_configurator.frontend_tkinter_scroll_frame import ScrollFrame


class LogQualityReportWindow(BaseWindow):
    """Displays log analysis results as a structured report card."""

    def __init__(self, root_tk: tk.Tk | tk.Toplevel, summary: LogSummary) -> None:
        super().__init__(root_tk)
        self.summary = summary
        self.root.title(_("Log Quality Report"))
        self.root.geometry(self.calculate_scaled_geometry(900, 620))
        self.center_window(self.root, root_tk)
        self.root.resizable(width=True, height=True)

        self._build_stats_strip()
        self._build_vehicle_strip()
        self._build_tabs()

    @staticmethod
    def _clean_devtype(name: str) -> str:
        """Strip DEVTYPE_ prefix and category prefix from device type names."""
        for prefix in ("DEVTYPE_INS_", "DEVTYPE_BARO_", "DEVTYPE_AIRSPEED_", "DEVTYPE_"):
            if name.startswith(prefix):
                return name[len(prefix):]
        return name

    @staticmethod
    def _fmt_duration(sec: float | None) -> str:
        if sec is None:
            return "N/A"
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


    def _build_stats_strip(self) -> None:
        outer = ttk.Frame(self.main_frame)
        outer.pack(side=tk.TOP, fill=tk.X, expand=False, padx=(8, 8), pady=(6, 0))

        pm = self.summary.pm_status
        stats = [
            (_("Flight time"), self._fmt_duration(self.summary.flight_duration_sec)),
            (_("Log size"),    self._fmt_filesize(self.summary.file_size_bytes)),
            (_("Messages"),    str(self.summary.total_messages)),
            (_("Msg types"),   str(self.summary.message_types)),
            (_("Parameters"),  str(self.summary.parameter_count)),
            (_("Avg CPU"),     f"{pm.average_cpu_load:.1f}%"         if pm else "N/A"),
            (_("Peak CPU"),    f"{pm.peak_cpu_load:.1f}%"            if pm else "N/A"),
            (_("Free mem"),    f"{pm.free_memory_bytes // 1024} KB"   if pm else "N/A"),
            (_("Long loops"),  str(pm.scheduler_long_loops)          if pm else "N/A"),
        ]

        for i, (label_text, value_text) in enumerate(stats):
            cell = ttk.Frame(outer)
            cell.pack(side=tk.LEFT, padx=(10, 10), pady=(4, 4))
            ttk.Label(cell, text=label_text, foreground="gray").pack(side=tk.TOP, anchor=tk.W)
            ttk.Label(cell, text=value_text, style="Bold.TLabel").pack(side=tk.TOP, anchor=tk.W)
            if i < len(stats) - 1:
                ttk.Separator(outer, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, pady=(4, 4))

        ttk.Separator(self.main_frame, orient=tk.HORIZONTAL).pack(
            side=tk.TOP, fill=tk.X, padx=(4, 4), pady=(4, 0)
        )


    def _build_vehicle_strip(self) -> None:
      outer = ttk.Frame(self.main_frame)
      outer.pack(side=tk.TOP, fill=tk.X, expand=False, padx=(8, 8), pady=(4, 0))

      hw = self.summary.hardware_report
      v  = hw.vehicle if hw else None

      firmware_base = "N/A"
      release_url   = None
      if v and v.vehicle_type and v.major is not None:
          firmware_base = f"{v.vehicle_type} {v.major}.{v.minor}.{v.patch}"
          release_url = (
              f"https://github.com/ArduPilot/ardupilot/releases/tag/"
              f"{v.vehicle_type}-{v.major}.{v.minor}.{v.patch}"
          )

      fc    = v.flight_controller if v and v.flight_controller else "Unknown FC"
      board = hw.board_name       if hw and hw.board_name      else "Unknown board"
      os_s  = (v.oper_sys[:50] + "...") if v and v.oper_sys and len(v.oper_sys) > 50 else (v.oper_sys or "")

      # Row 1 — firmware + hash link + FC
      row1 = ttk.Frame(outer)
      row1.pack(side=tk.TOP, fill=tk.X, anchor=tk.W, pady=(2, 0))

      ttk.Label(row1, text=_("Firmware:"), foreground="gray").pack(side=tk.LEFT, padx=(10, 4))
      ttk.Label(row1, text=firmware_base, style="Bold.TLabel").pack(side=tk.LEFT)

      if v and v.vehicle_type and release_url:
        short_type = v.vehicle_type.replace("Ardu", "")
        version_str = f"{short_type}-{v.major}.{v.minor}.{v.patch}"
        release_url = f"https://github.com/ArduPilot/ardupilot/tree/{version_str}"

        link_label = ttk.Label(
            row1,
            text=f"  ({version_str})",
            foreground="blue",
            cursor="hand2",
            font=("TkDefaultFont", self.default_font_size, "underline"),
        )
        link_label.pack(side=tk.LEFT)
        link_label.bind("<Button-1>", lambda _e, url=release_url: webbrowser.open(url))
        show_tooltip(link_label, _("Open release page on GitHub"))

      ttk.Separator(row1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(12, 12), pady=(2, 2))
      ttk.Label(row1, text=_("FC:"), foreground="gray").pack(side=tk.LEFT, padx=(0, 4))
      ttk.Label(row1, text=fc, style="Bold.TLabel").pack(side=tk.LEFT)

      # Row 2 — board + OS
      row2 = ttk.Frame(outer)
      row2.pack(side=tk.TOP, fill=tk.X, anchor=tk.W, pady=(2, 4))

      ttk.Label(row2, text=_("Board:"), foreground="gray").pack(side=tk.LEFT, padx=(10, 4))
      ttk.Label(row2, text=board, style="Bold.TLabel").pack(side=tk.LEFT)

      if os_s:
          ttk.Separator(row2, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(12, 12), pady=(2, 2))
          ttk.Label(row2, text=_("OS:"), foreground="gray").pack(side=tk.LEFT, padx=(0, 4))
          ttk.Label(row2, text=os_s, style="Bold.TLabel").pack(side=tk.LEFT)

      ttk.Separator(self.main_frame, orient=tk.HORIZONTAL).pack(
          side=tk.TOP, fill=tk.X, padx=(4, 4), pady=(4, 0)
      )


    def _build_tabs(self) -> None:
        notebook = ttk.Notebook(self.main_frame)
        notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=(4, 4), pady=(4, 4))

        quality_frame = ttk.Frame(notebook)
        notebook.add(quality_frame, text=_("Quality"))
        self._build_quality_tab(quality_frame)

        hardware_frame = ttk.Frame(notebook)
        notebook.add(hardware_frame, text=_("Hardware"))
        self._build_hardware_tab(hardware_frame)

    # Quality check
    def _build_quality_tab(self, parent: ttk.Frame) -> None:
        scroll_container = ScrollFrame(parent)
        scroll_container.pack(fill=tk.BOTH, expand=True)
        inner = scroll_container.view_port

        # ---- subsystem quality results ----
        ttk.Label(inner, text=_("Subsystem quality"), style="Bold.TLabel").pack(
            anchor=tk.W, padx=(12, 8), pady=(10, 2)
        )
        ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=(12, 8))

        for result in self.summary.quality_results:
            self._quality_result_row(inner, result)

        ttk.Label(inner, text=_("Configuration step coverage"), style="Bold.TLabel").pack(
            anchor=tk.W, padx=(12, 8), pady=(14, 2)
        )
        ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=(12, 8))

        for step_result in self.summary.step_results:
            self._step_result_row(inner, step_result)

    def _quality_result_row(self, parent: ttk.Frame, result: LogQualityResult) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, padx=(12, 8), pady=(6, 0))

        text_label = "[OK]" if result.state == "info" else "[WARN]"
        color = "darkgreen" if result.state == "info" else "red"
        ttk.Label(row, text=text_label, foreground=color, font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=(4, 12))

        text_frame = ttk.Frame(row)
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(text_frame, text=result.name, style="Bold.TLabel").pack(anchor=tk.W)
        reason_label = ttk.Label(text_frame, text=result.reason, foreground="gray")
        reason_label.pack(anchor=tk.W, fill=tk.X)
        text_frame.bind("<Configure>", lambda e, l=reason_label: l.configure(wraplength=max(1, e.width - 10)))  # noqa: E741

        if result.issues:
            count_label = ttk.Label(row, text=f"{len(result.issues)} issue(s)", foreground="orange")
            count_label.pack(side=tk.RIGHT, padx=(8, 4))
            tooltip_text = "\n".join(f"- {i.message}" for i in result.issues)
            show_tooltip(count_label, tooltip_text)

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=(12, 8), pady=(6, 0))

    def _step_result_row(self, parent: ttk.Frame, result: StepValidationResult) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, padx=(12, 8), pady=(3, 0))

        text_label = "[PASS]" if result.valid else "[FAIL]"
        color = "darkgreen" if result.valid else "darkorange"
        ttk.Label(row, text=text_label, foreground=color, font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT, padx=(4, 12))

        display_name = result.name or result.step
        label = ttk.Label(row, text=display_name)
        label.pack(side=tk.LEFT, anchor=tk.W, fill=tk.X, expand=True)
        row.bind("<Configure>", lambda e, l=label: l.configure(wraplength=max(1, e.width - 80)))

        if not result.valid:
            issues_lines = [
                issue
                for msg_result in result.message_results.values()
                for issue in msg_result.issues
            ]
            if issues_lines:
                show_tooltip(row, "\n".join(f"- {i}" for i in issues_lines))

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=(12, 8), pady=(3, 0))


    def _build_hardware_tab(self, parent: ttk.Frame) -> None:
        hw = self.summary.hardware_report
        if hw is None:
            ttk.Label(parent, text=_("No hardware data available"), foreground="gray").pack(padx=16, pady=16)
            return

        scroll_container = ScrollFrame(parent)
        scroll_container.pack(fill=tk.BOTH, expand=True)
        inner = scroll_container.view_port

        if hw.imus:
            ttk.Label(inner, text=_("IMUs"), style="Bold.TLabel").pack(anchor=tk.W, padx=16, pady=(12, 2))
            ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16)
            for imu in hw.imus:
                self._hw_section(inner, f"IMU {imu.instance}", [
                    (_("Accel"), self._clean_devtype(imu.accel_name or "Unknown")),
                    (_("Gyro"),  self._clean_devtype(imu.gyro_name  or "Unknown")),
                    (_("Bus type"), imu.accel_bus_type or "Unknown"),
                    (_("Accel calibrated"), str(imu.accel_calibrated)),
                    (_("Gyro calibrated"), str(imu.gyro_calibrated)),
                    (_("Temp calibrated"), str(imu.accel_temp_calibrated)),
                    (_("Accel healthy"), str(imu.accel_healthy)),
                    (_("Gyro healthy"), str(imu.gyro_healthy)),
                ])

        if hw.compasses:
            ttk.Label(inner, text=_("Compasses"), style="Bold.TLabel").pack(anchor=tk.W, padx=16, pady=(14, 2))
            ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16)
            for compass in hw.compasses:
                self._hw_section(inner, f"Compass {compass.instance}", [
                    (_("Chip"), self._clean_devtype(compass.name or "Unknown")),
                    (_("Bus type"), self._clean_devtype(compass.bus_type or "Unknown")),
                    (_("External"), str(compass.external)),
                    (_("Calibrated"), str(compass.calibrated)),
                    (_("Motor calibrated"), str(compass.motor_calibrated)),
                    (_("Healthy"), str(compass.healthy)),
                ])

        if hw.baros:
            ttk.Label(inner, text=_("Barometers"), style="Bold.TLabel").pack(anchor=tk.W, padx=16, pady=(14, 2))
            ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16)
            for baro in hw.baros:
                self._hw_section(inner, f"Baro {baro.instance}", [
                    (_("Chip"), self._clean_devtype(baro.name or "Unknown")),
                    (_("Bus type"),self._clean_devtype(baro.bus_type or "Unknown")),
                    (_("Wind compensation"), str(baro.wind_compensation)),
                    (_("Healthy"), str(baro.healthy)),
                ])

        if hw.airspeed_sensors:
            ttk.Label(inner, text=_("Airspeed sensors"), style="Bold.TLabel").pack(anchor=tk.W, padx=16, pady=(14, 2))
            ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16)
            for arspd in hw.airspeed_sensors:
                self._hw_section(inner, f"Airspeed {arspd.instance}", [
                    (_("Type"), arspd.sensor_type or "Unknown"),
                    (_("In use"), str(arspd.use)),
                    (_("Healthy"), str(arspd.healthy)),
                ])

    def _hw_section(self, parent: ttk.Frame, title: str, fields: list[tuple[str, str]]) -> None:
        ttk.Label(parent, text=title, style="Bold.TLabel").pack(anchor=tk.W, padx=24, pady=(6, 2))
        for label_text, value_text in fields:
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, padx=36, pady=(1, 1))
            ttk.Label(row, text=label_text, foreground="gray", width=22, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(row, text=value_text, anchor=tk.W, wraplength=400).pack(side=tk.LEFT, fill=tk.X, expand=True)


    def run(self) -> None:
        self.root.mainloop()