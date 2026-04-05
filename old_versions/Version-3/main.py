import sys
from src.parser.parser import parse_log
from src.engines.phy_engine import process_physics
from src.validator import PhysicsValidator
from ml.ml_analyser import TelemetryMLAnalyzer
from src.diagnostics import Fuser

# TODO: check oscillation cases here
# TODO: test with 00000082.bin log

def run_diagnostics(log_filepath, model_filepath="models/telemetry_rf_model.pkl"):
    print("running log", log_filepath)

    # 1. Extract raw MAVLink signals
    raw_data = parse_log(log_filepath)
    # parser should ideally do this but for safety
    if not raw_data.get("signals") or not raw_data["signals"].get("ATT"):
        print("Error: Could not extract required target messages from log.")
        return

    # 2. Extract features and convert to Probabilistic Z-Scores
    df = process_physics(raw_data)
    if df.empty:
        print("Error: No usable physics data calculated.")
        return

    # 3. Parallel Detection Layer
    validator = PhysicsValidator(z_threshold=3.0)
    physics_events = validator.extract_events(df)
    physics_events = validator.merge_overlapping_events(physics_events)

    # future: add oscillation classifier (PID instability)
    ml_analyzer = TelemetryMLAnalyzer()
    ml_analyzer.load_model(model_filepath)
    ml_events = ml_analyzer.extract_events(df) 
    
    # 4. FDIR Causal Graph Layer
    fusion = Fuser()
    merged_events = fusion.fuse_events(physics_events, ml_events)
    
    if not merged_events:
        print("no faults found")
        return

    final_report = fusion.diagnose(merged_events, df)
    
    # 5. Output Final Report (Passing the events so you can see the timeline)
    print(fusion.format_terminal_report(final_report, merged_events))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("give log file path")
        sys.exit(1)

    run_diagnostics(sys.argv[1])