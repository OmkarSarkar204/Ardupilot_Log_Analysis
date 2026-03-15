import pandas as pd
import numpy as np
import joblib 
from sklearn.ensemble import RandomForestClassifier

class TelemetryMLAnalyzer:
    def __init__(self, probability_threshold=0.75):
        # might tune later
        self.probability_threshold = probability_threshold
        self.model = RandomForestClassifier(
            n_estimators=100, 
            max_depth=5,       
            min_samples_leaf=4, 
            class_weight="balanced", 
            random_state=73
        )
        self.is_trained = False

        ## future: add gyro stuff + oscillation features
        # plan to keep the features in a separate file for diff vehicles 
        self.feature_cols = [
            'motor_spread', 
            'roll_error', 
            'volt_sag', 
            'power_watts',
            'spread_mean_3s', 
            'sag_max_3s', 
            'sag_slope'
            # add more features for drone
        ]

    def load_model(self, filepath):
        # print("loading model" , filepath) ## debug
        self.model = joblib.load(filepath) 
        self.is_trained = True
        
    def save_model(self, filepath):
        if self.is_trained:
            joblib.dump(self.model, filepath)

    def train(self, training_dataframes):
        # print("training ml model on telemetry data..")  ## debug
        X_train = []
        y_train = []
        
        for df in training_dataframes:
            df = df.replace([np.inf, -np.inf], np.nan)
            valid_df = df.dropna(subset=self.feature_cols + ['label'])
            if not valid_df.empty:
                X_train.append(valid_df[self.feature_cols])
                y_train.append(valid_df['label'])
                
        if X_train:
            X = pd.concat(X_train, ignore_index=True)
            y = pd.concat(y_train, ignore_index=True)
            self.model.fit(X, y)
            self.is_trained = True

    def extract_events(self, df):
        if self.model is None or not self.is_trained: 
            # print("ml model not ready?? skipping ml detection")  ## debug
            return []
            
        probs = self.model.predict_proba(df[self.feature_cols])
        classes = list(self.model.classes_)
        
        df['ml_pred'] = 0 
        ## motor anomaly
        if 1 in classes:
            df.loc[probs[:, classes.index(1)] > self.probability_threshold, 'ml_pred'] = 1
         ## battery anomaly
        if 2 in classes:
            df.loc[probs[:, classes.index(2)] > self.probability_threshold, 'ml_pred'] = 2
        
        events = []
        for label, event_name in [(1, 'ml_motor_anomaly'), (2, 'ml_battery_anomaly')]: # next is oscillation for the 0000082.BIN
            mask = df['ml_pred'] == label
            if not mask.any(): 
                continue
                
            blocks = (mask != mask.shift()).cumsum()
            for _, block_df in df[mask].groupby(blocks):
                duration = block_df['time_sec'].iloc[-1] - block_df['time_sec'].iloc[0]
                
                if duration > 1.0:
                    events.append({
                        'start_time': block_df['time_sec'].iloc[0],
                        'end_time': block_df['time_sec'].iloc[-1],
                        'duration': round(duration, 3),
                        'event_type': event_name,
                        'severity_z': 5.0, # just as a placeholder will change with prob or z score if needed
                        'sources': ['ml_analyzer']
                    })
        return sorted(events, key=lambda x: x['start_time'])
