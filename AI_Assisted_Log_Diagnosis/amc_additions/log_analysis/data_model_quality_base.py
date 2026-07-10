from dataclasses import dataclass
from typing import Any
from ardupilot_methodic_configurator import _
from ardupilot_methodic_configurator.log_analysis.backend_log_extraction import(
  LogData,
)

@dataclass
class LogQualityResult:
    """Result produced by a subsystem quality model (battery, GPS, etc.)."""

    available: bool
    state: str
    reason: str
    config_step: str
    issues: list[str]
    name: str


class BaseLogQualityAnalysisModel:
  """Base class for log analysis models."""

  NAME = ""
  CONFIG_STEP = ""
  LOG_BIT = 0

  def __init__(self, log_data: LogData, parameters: dict[str, float],
               vehicle_components: dict[str, Any] | None = None) -> None:
    self.log_data = log_data
    self.parameters = parameters or {}
    self.vehicle_components = vehicle_components or {}

  def build_result(self, issues: list[str]) -> LogQualityResult:
        """Build a standard analysis result."""
        return LogQualityResult(
            available=True,
            state="info" if not issues else "warning",
            reason=_("{name} data present and good for analysis").format(name=self.NAME)
            if not issues
            else _("{name} data has quality issues").format(name=self.NAME),
            config_step="" if not issues else self.CONFIG_STEP,
            issues=issues,
            name=self.NAME
        )

