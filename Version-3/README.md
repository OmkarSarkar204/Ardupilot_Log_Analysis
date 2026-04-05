# Prototype Progress

A working prototype of the diagnostic system was developed during the pre-GSoC period to validate core design decisions. The codebase is functional and open-source, focused on verifying the system architecture. Production-level optimizations, robust error handling, and hardened coding practices will be added during the full development phase.

Three versions were built during this phase. Version 3 was locked as the reference architecture going forward.


## Modules

### `parser.py` - Data Extraction

Reads raw telemetry from `.BIN` log files. Processes logs in a streamed manner to avoid loading entire files into memory, which keeps large log handling efficient.

- Reads all available telemetry messages without early filtering
- Extracts attitude, battery, and actuator output fields
- Identifies basic metadata: timestamps and available parameters



### `phy_engine.py` - Feature Generation

Converts raw telemetry into structured, analysis-ready data. Because sensors log at different rates, direct comparison is unreliable. The module organizes data into fixed time windows and aligns all signals within each window.

**Alignment:**
- Data is grouped into fixed time intervals
- Signals are aligned within each interval
- Missing values are filled via interpolation or last-known-value carry-forward

**Computed Features:**
- Rate of change of signals
- Difference between expected and actual values
- Z-score normalization

```python
def compute_z_score(x, mean, std):
    if std == 0:
        return 0
    return (x - mean) / std
```

**Domain-Specific Features:**

- **Attitude Error:**

$$e_{pitch} = |pitch_{desired} - pitch_{actual}|$$

- **Motor Imbalance:** Difference between motor outputs to detect uneven thrust distribution
- **Battery Variation:** Change in voltage over time to catch sudden drops

```python
# Pitch error
pitch_error = abs(desired_pitch - actual_pitch)

# Roll error
roll_error = abs(desired_roll - actual_roll)

# Rate of change (example: altitude)
climb_rate = (current_altitude - previous_altitude) / delta_time

# Z-score normalization
if std_dev != 0:
    z_score = (value - mean) / std_dev
else:
    z_score = 0
```



### `validator.py`  Physics Validator

Performs rule-based detection using the engineered features. Rules are grounded in expected physical behavior and compare control inputs against observed system response.

- Control inputs are compared with observed outputs
- Differences between expected and actual behavior are evaluated
- Conditions are checked across multiple time windows
- A condition must persist for a defined duration before it is flagged (no single-point reactions)

**Example Conditions:**
- High throttle with decreasing altitude
- Large gap between desired and actual attitude
- Sudden battery voltage drop under load

```python
# Thrust-related issue
if throttle > 0.9 and climb_rate < 0:
    thrust_issue = True

# Attitude instability
if pitch_error > threshold or roll_error > threshold:
    attitude_issue = True

# Battery drop detection
if voltage_drop > voltage_threshold:
    battery_issue = True
```

**Output:** A list of detected events with their time ranges, passed downstream to the aggregation stage.



### `ml_analyser.py`  ML Module

Runs in parallel with the physics validator. Currently implemented using a Random Forest classifier.

Ingests the engineered time-window DataFrame directly from `phy_engine.py`  it does not touch raw logs.

- Extracts specific engineered features from the DataFrame
- Predicts probability of specific failure classes (motor anomaly, battery anomaly)
- Applies a strict probability threshold to filter low-confidence predictions
- Groups predictions into contiguous time blocks; a prediction must be sustained for more than 1.0 second to be recorded as an event

```python
self.feature_cols = [
    'motor_spread', 'roll_error', 'volt_sag', 'power_watts',
    'spread_mean_3s', 'sag_max_3s', 'sag_slope'
]

def extract_events(self, df):
    probs = self.model.predict_proba(df[self.feature_cols])
    classes = list(self.model.classes_)

    df['ml_pred'] = 0

    if 1 in classes:
        df.loc[probs[:, classes.index(1)] > self.probability_threshold, 'ml_pred'] = 1

    if 2 in classes:
        df.loc[probs[:, classes.index(2)] > self.probability_threshold, 'ml_pred'] = 2
```

```python
if duration > 1.0:
    events.append({
        'start_time': block_df['time_sec'].iloc[0],
        'end_time':   block_df['time_sec'].iloc[-1],
        'duration':   round(duration, 3),
        'event_type': event_name,
        'sources':    ['ml_model']
    })
```

**Output:** Standardized event array (`start_time`, `end_time`, `event_type`)  identical format to the Physics Validator output, so both feed cleanly into the aggregation stage.



### `diagnostics.py` - Event Aggregation and Diagnosis

Combines outputs from the Physics Validator and the ML Module. Because both upstream modules produce events in the same format, this layer processes them without needing to know their source.

**Event Aggregation (Time Overlap)**

All detections are sorted chronologically. If events of the same type occur within 2.0 seconds of each other, they are merged into a single continuous event.

```python
for prev in reversed(merged):
    gap = current['start_time'] - prev['end_time']

    if current['event_type'].lower() == prev['event_type'].lower() and gap <= 2.0:
        prev['end_time'] = max(prev['end_time'], current['end_time'])
        prev['duration'] = round(prev['end_time'] - prev['start_time'], 3)
        matched = True
        break
```

**Root Cause Logic**

After aggregation, the combined timeline is analyzed to determine root cause. Events are evaluated based on order, duration, and cross-source agreement rather than treated in isolation.

- Events shorter than 0.5 seconds are discarded to prevent sensor glitches from triggering false diagnoses
- A physical anomaly below the continuous duration threshold is discarded unless the ML module also detected it

```python
# Discard weak physics detections if ML did not confirm
if not has_ml_motor and max_continuous_motor < dynamic_threshold:
    motor_score = 0

if not has_ml_batt and max_continuous_batt < dynamic_threshold:
    batt_score = 0

# Root cause: whichever subsystem showed more severe confirmed degradation
if batt_score == 0 and motor_score == 0:
    return "Healthy"

if batt_score > motor_score:
    return "Battery Failure"
else:
    return "Motor Failure"
```



### `main.py` - Pipeline Orchestrator

Controls data flow across all stages in a fixed sequence.

```
1. Raw log  ->  Data Extraction  (parser.py)
2. Extracted data  ->  Feature Generation  (phy_engine.py)
3. Features  ->  Physics Validator  (validator.py)    [parallel]
             ->  ML Module          (ml_analyser.py)  [parallel]
4. Both outputs  ->  Aggregation + Diagnosis  (diagnostics.py)
```

```python
raw_data = parse_log(log_filepath)

df = process_physics(raw_data)

physics_events = validator.extract_events(df)
ml_events      = ml_analyzer.extract_events(df)
```



## Sample Output

Tested on a real-world motor failure log:

```
events:

PHY motor_spread     24.0  -> 27.6   dur 3.6
PHY roll_error       24.1  -> 39.0   dur 14.9
PHY motor_spread     65.2  -> 69.3   dur 4.1
PHY roll_error       65.2  -> 83.5   dur 18.3
PHY motor_spread    113.8  -> 117.9  dur 4.1
PHY roll_error      113.9  -> 155.7  dur 41.8
PHY motor_spread    127.8  -> 155.7  dur 27.9
ML  ml_motor_anomaly 128.0 -> 155.7  dur 27.7
PHY power_delta     145.3  -> 145.8  dur 0.5
PHY power_delta     151.5  -> 152.0  dur 0.5

result:

motor failure
```
