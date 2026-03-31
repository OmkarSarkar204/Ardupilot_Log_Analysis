## V2

This version moves the project from a purely physics based detector (v1) to a system where both a machine learning model and a physics validator analyse the flight logs.

### What was added in v2

- **Random Forest failure classifier**
  - trained on logs from Arducopter SITL
  - predicts: Healthy / Motor Failure / Battery Failure

- **physics validation**
  - instead of hardcoded, thresholds are calculated from the flight baseline
  - uses the first part of the log to estimate normal behaviour (not efficient)

- **Dual-engine verification**
  - ML model predicts possible failure
  - Physics validator independently checks sensor conditions (not efficeint has to look to the full flight log)
  - final decision only happens if both agree

- **Feature engineering**
  - motor spread
  - roll error
  - voltage sag
  - power usage

- **Full BIN log pipeline**
  - parser reads ArduPilot logs
  - physics engine extracts signals
  - ML model classifies behaviour
  - validator confirms physical plausibility

### What v2 can detect

Currently the system can identify:

- Motor imbalance / thrust loss
- Battery voltage collapse
- Healthy flights

and outputs the timestamp where the anomaly first appears.

### What v2 still lacks

This version still has several limitations:

- detection happens per-row, not as continuous events
- system does not yet analyse the entire flight timeline
- ML and physics only agree on the same timestamp, not over windows
- root cause reasoning is limited (e.g. battery sag vs motor response)
- only a few sensor signals are used

### Next goal (v3)

The next version will move toward event-based log reasoning:

- detect failure windows instead of single samples (Event Clustering)
- allow ML and physics to operate independently
- analyse the full flight timeline
