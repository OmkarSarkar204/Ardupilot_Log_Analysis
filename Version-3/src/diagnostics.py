class Fuser:

    def fuse_events(self, physics_events, ml_events):

        # combine events from physics + ml
        all_events = sorted(physics_events + ml_events, key=lambda x: x['start_time'])

        if not all_events:
            return []

        merged = []

        for current in all_events:

            matched = False

            # check backwards so latest events merge first
            for prev in reversed(merged):

                gap = current['start_time'] - prev['end_time']

                # same event type and close enough in time
                if current['event_type'].lower() == prev['event_type'].lower() and gap <= 2.0:

                    prev['end_time'] = max(prev['end_time'], current['end_time'])
                    prev['duration'] = round(prev['end_time'] - prev['start_time'], 3)

                    # debug maybe check later
                    # print("merge happening", prev['event_type'])

                    matched = True
                    break

            if not matched:
                merged.append(current)

        return merged


    def diagnose(self, fused_events, df):

        if not fused_events:
            return "Healthy"

        # event categories
        battery_terms = {'volt_sag', 'ml_battery_anomaly', 'power_delta'}
        motor_terms = {'motor_spread', 'ml_motor_anomaly'}

        # ignore very tiny glitches
        file_timeline = sorted(
            [e for e in fused_events if e['duration'] >= 0.5],
            key=lambda x: x['start_time']
        )

        if not file_timeline:
            return "Healthy"

        batt_score = 0
        motor_score = 0

        has_ml_motor = False
        has_ml_batt = False

        max_continuous_motor = 0
        max_continuous_batt = 0

        # build dynamic threshold from event durations
        physical_durations = [
            e['duration']
            for e in file_timeline
            if 'ml' not in e['event_type'].lower()
        ]

        if len(physical_durations) > 2:

            import statistics

            mean_dur = statistics.mean(physical_durations)
            std_dur = statistics.stdev(physical_durations)

            # floor to avoid tiny noise spikes
            dynamic_threshold = max(5.0, mean_dur + (3 * std_dur))

        else:
            dynamic_threshold = 5.0

        # scan events
        for e in file_timeline:

            etype = e['event_type'].lower()

            if etype in battery_terms:

                batt_score += e['duration']

                if 'ml' in etype:
                    has_ml_batt = True

                if 'volt_sag' in etype and e['duration'] > max_continuous_batt:
                    max_continuous_batt = e['duration']


            elif etype in motor_terms:

                motor_score += e['duration']

                if 'ml' in etype:
                    has_ml_motor = True

                if 'motor_spread' in etype and e['duration'] > max_continuous_motor:
                    max_continuous_motor = e['duration']


        # filter weak detections if ML didn't confirm
        if not has_ml_motor and max_continuous_motor < dynamic_threshold:
            motor_score = 0

        if not has_ml_batt and max_continuous_batt < dynamic_threshold:
            batt_score = 0


        # nothing serious
        if batt_score == 0 and motor_score == 0:
            return "Healthy"


        # whichever system suffered more wins
        if batt_score > motor_score:
            return "Battery Failure"
        else:
            return "Motor Failure"



    def format_terminal_report(self, state, events):

        report = ["\nFLIGHT LOG ANALYSIS REPORT",]

        report.append("Flight Timeline")

        if not events:
            report.append("  No sustained anomalies detected.")

        else:
            for e in events:

                if e['duration'] >= 0.5:

                    src = "ML" if "ml_" in e['event_type'] else "PHY"

                    line = str(round(e["start_time"],1)) + "s --> "
                    line += str(round(e["end_time"],1)) + "s "
                    line += src + " " + e["event_type"]
                    line += " dur " + str(round(e["duration"],1))

                    report.append(line)

        report.append(f" ROOT CAUSE: {state.upper()}")

        return "\n".join(report)