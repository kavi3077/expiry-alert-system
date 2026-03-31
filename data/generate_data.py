import pandas as pd
import numpy as np

rows = 10000

data = {
    "days_left": np.random.randint(1, 30, rows),
    "stock": np.random.randint(10, 200, rows),
    "price": np.random.randint(20, 500, rows),
    "avg_sales": np.random.randint(1, 50, rows),
    "discount": np.random.randint(0, 50, rows),  # %
    "season_demand": np.round(np.random.uniform(0.1, 1.0, rows), 2),
    "supplier_delay": np.random.randint(0, 10, rows),  # days
    "storage_temp": np.random.randint(0, 10, rows),  # °C (cold storage)
    "product_age": np.random.randint(1, 60, rows),  # days since manufacturing
    "category": np.random.randint(1, 6, rows)  # 5 categories
}

df = pd.DataFrame(data)

# Improved Risk Logic
df["risk"] = (
    (df["days_left"] < 7) &
    (df["stock"] > df["avg_sales"] * 3) &
    (df["discount"] < 20)
).astype(int)

df.to_csv("data/products.csv", index=False)

print("✅ Dataset with 10 features generated!")