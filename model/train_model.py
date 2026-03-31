import pandas as pd
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from sklearn.preprocessing import StandardScaler
import joblib

# Load dataset
df = pd.read_csv("data/products.csv")

# Features (10 inputs)
X = df[[
    "days_left", "stock", "price", "avg_sales",
    "discount", "season_demand", "supplier_delay",
    "storage_temp", "product_age", "category"
]].values

# Target
y = df["risk"].values

# ---------------- NORMALIZATION ----------------
scaler = StandardScaler()
X = scaler.fit_transform(X)

# Save scaler (IMPORTANT for prediction later)
joblib.dump(scaler, "model/scaler.pkl")

# ---------------- MODEL ----------------
model = Sequential()

model.add(Dense(16, input_dim=10, activation='relu'))
model.add(Dense(12, activation='relu'))
model.add(Dense(8, activation='relu'))
model.add(Dense(1, activation='sigmoid'))

# Compile
model.compile(
    loss='binary_crossentropy',
    optimizer='adam',
    metrics=['accuracy']
)

# Train
model.fit(X, y, epochs=20, batch_size=32)

# Save model
model.save("model/model.h5")

print("✅ Model trained with 10 features!")