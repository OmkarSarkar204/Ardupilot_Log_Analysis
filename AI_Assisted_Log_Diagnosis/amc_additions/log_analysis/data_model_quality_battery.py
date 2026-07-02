"""
Data model for battery quality check.

SPDX-FileCopyrightText: 2024-2026 Amilcar do Carmo Lucas <amilcar.lucas@iav.de>

SPDX-License-Identifier: GPL-3.0-or-later
"""

from dataclasses import dataclass
from typing import Any
from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import LogData

@dataclass
class LogBatteryQuality:
  available: bool
  state: str
  reason: str
  config_step: str
  issues: list[str]


class BatteryQualityModel:
  def __init__(self, log_data: LogData, parameters) -> None:
    self.log_data = log_data
    self.parameters = parameters

  def extract(self, records, field) -> list:
     return [r.get(field) for r in records if r.get(field) is not None]

  def build_result(self, issues: list[str]) -> LogBatteryQuality:
     return LogBatteryQuality(
        available=True,
        state="info" if not issues else "warning",
        reason="Battery data present and good for analysis" if not issues else "Battery data has quality issues",
        config_step="" if not issues else "10_battery_monitor.param",
        issues=issues
     )

  def check(self) -> LogBatteryQuality:
      records = self.log_data.raw_messages.get("BAT", [])

      if not records:
        return LogBatteryQuality(
          available=False,
          state="warning",
          reason="Battery telemetry (BAT) is not logged.",
          config_step="10_battery_monitor.param",
          issues=["No BAT messages found in log"],
        )
      issues: list[str] = []
      for check in (self.check_voltage, self.check_curr_total, self.check_current):
         issues += check(records)
      return self.build_result(issues)

  def check_voltage(self, records: Any) -> list[str]:  # noqa: ANN401
      issues = []
      volts = self.extract(records, "Volt")
      if not volts:
          issues.append("Voltage values missing from BAT records")
      elif max(volts) == 0:
          issues.append("Voltage is zero throughout sensor may not be reading")
      elif max(volts) == min(volts):
          issues.append("Voltage shows no variation")

      return issues

  def check_current(self, records: Any) -> list[str]:
    issues = []
    current = self.extract(records, "Curr")
    if not current:
      issues.append("Current values missing from BAT records")
    return issues

  def check_curr_total(self, records: Any) -> list[str]:
    issues = []
    cur_tot = self.extract(records, "CurrTot")
    if not cur_tot:
       issues.append("CurrTot missing from BAT")
    elif max(cur_tot) == min(cur_tot):
       issues.append("Total current did not increased during fight")
    return issues

  def check_parameters(self) -> list[str]:
      issues = []
      monitor = self.parameters.get("BATT_MONITOR")

      if monitor is None:
          return issues

      if monitor == 0:
          issues.append("Battery monitoring disabled")
          return issues

      if self.parameters.get("BATT_LOW_VOLT") == 0:
          issues.append("Low-voltage failsafe disabled")
      if self.parameters.get("BATT_CRT_VOLT") == 0:
          issues.append("Critical-voltage failsafe disabled")

      return issues
