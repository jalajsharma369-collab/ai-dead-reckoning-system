import pandas as pd

data = pd.read_csv("sensor_data.csv")

print(data.head())
print(data.columns.tolist())
print(data.shape)
print(data.isnull().sum())