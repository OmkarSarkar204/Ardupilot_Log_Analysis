from dataclasses import dataclass
from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import LogData

@dataclass
class LogBatteryQuality:
  available: bool
  state: str
  reason: str
  config_step: str
  issues: list[str]


class BatteryQualityModel:
  def __init__(self, log_data, parameters) -> None:
    self.log_data = log_data
    self.parameters = parameters

  def check(self) -> LogBatteryQuality:
    record = self.log_data.raw_messages.get("BAT", [])

    if not record:
      return LogBatteryQuality(
        available=False,
        state="warning",
        reason="Battery telemetry (BAT) is not logged.",
        config_step="10_battery_monitor.param",
        issues=["No BAT messages found in log"],
      )
