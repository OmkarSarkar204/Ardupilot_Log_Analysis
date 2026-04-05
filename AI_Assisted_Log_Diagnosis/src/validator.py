class PhysicsValidator:
    def __init__(self, z_threshold=3.0):
        # Calculating Z score using the Json Data dynanically and using the 3 sigma rule to cut the noise a bit(will improve)
        self.z_threshold = z_threshold

    def extract_events(self, df):
        if df.empty:
            return []

        events = []
        
        # Dynamically discover all standardized feature columns
        z_cols = [col for col in df.columns if col.endswith('_zscore')]
        
        if len(df) > 1:
            dt = df['time_sec'].diff().median()
        else:
            dt = 0.1
            
        min_duration = dt * 3  

        for col in z_cols:
            feature_name = col.replace('_zscore', '')
            
            # Vectorized Thresholding
            df[f'{feature_name}_fault'] = df[col].abs() > self.z_threshold
            
            # Grouping
            df['fault_block'] = (df[f'{feature_name}_fault'] != df[f'{feature_name}_fault'].shift(1)).cumsum()
            
            faults_only = df[df[f'{feature_name}_fault']]
            
            if faults_only.empty:
                continue
                
            blocks = faults_only.groupby('fault_block').agg(
                start_time=('time_sec', 'min'),
                end_time=('time_sec', 'max'),
                peak_zscore=(col, lambda x: x.abs().max()) 
            ).reset_index(drop=True)

            for _, row in blocks.iterrows():
                duration = row['end_time'] - row['start_time']
                
                if duration >= min_duration or row['peak_zscore'] > (self.z_threshold * 1.5):
                    events.append({
                        "event_type": feature_name,
                        "start_time": row['start_time'],
                        "end_time": row['end_time'],
                        "duration": round(duration, 3),
                        "severity_z": round(row['peak_zscore'], 2),
                        "sources": ["probabilistic_fdir"]
                    })

        return sorted(events, key=lambda x: x['start_time'])

    def merge_overlapping_events(self, sorted_events):
        if not sorted_events:
            return []
            
        merged = [sorted_events[0]]
        
        for current in sorted_events[1:]:
            prev = merged[-1]
            
            time_gap = current['start_time'] - prev['end_time']
            
            if current['event_type'] == prev['event_type'] and time_gap <= 0.15:
                # Ectending window to max severe cases.
                prev['end_time'] = max(prev['end_time'], current['end_time'])
                prev['duration'] = round(prev['end_time'] - prev['start_time'], 3)
                prev['severity_z'] = max(prev['severity_z'], current['severity_z'])
                prev['sources'] = list(set(prev['sources'] + current['sources']))
            else:
                merged.append(current)
                
        return merged