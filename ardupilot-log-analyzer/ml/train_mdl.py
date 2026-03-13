import os
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix


DATA_PATH = "data/datasets/master_dataset.csv"

print("Loading dataset...")
df = pd.read_csv(DATA_PATH)

print(f"Dataset size: {len(df)} rows")

df = df.sample(frac=1, random_state=42).reset_index(drop=True)


FEATURES = [
    "motor_spread",
    "roll_error",
    "volt_sag",
    "power_watts"
]

X = df[FEATURES]
y = df["label"]

print("\nClass distribution:")
print(y.value_counts())


# --------------------------------------------------
# 4. Train/Test Split
# --------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    stratify=y,
    random_state=42
)

print(f"\nTraining samples: {len(X_train)}")
print(f"Testing samples: {len(X_test)}")


model = RandomForestClassifier(
    n_estimators=100,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)


print("\nTraining model...")
model.fit(X_train, y_train)


print("\nEvaluating model...")

y_pred = model.predict(X_test)

print("\n--- Classification Report ---")
print(classification_report(y_test, y_pred))

print("\n--- Confusion Matrix ---")
print(confusion_matrix(y_test, y_pred))


print("\nFeature Importance:")

importance = pd.Series(
    model.feature_importances_,
    index=FEATURES
).sort_values(ascending=False)

print(importance)


MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "drone_fault_model.pkl")

os.makedirs(MODEL_DIR, exist_ok=True)

joblib.dump(model, MODEL_PATH)

print(f"\nModel saved to {MODEL_PATH}")