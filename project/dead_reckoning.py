import pandas as pd
import math

# Load sensor data
data = pd.read_csv("sensor_data.csv")

# Earth radius in meters
EARTH_RADIUS = 6371000

# Starting position
start_lat = data.iloc[0]["latitude"]
start_lon = data.iloc[0]["longitude"]

estimated_lat = start_lat
estimated_lon = start_lon

estimated_positions = []

for i in range(len(data)):

    if i == 0:
        estimated_positions.append(
            [estimated_lat, estimated_lon]
        )
        continue

    # Time difference
    dt = data.iloc[i]["timestamp"] - data.iloc[i - 1]["timestamp"]

    # Speed from sensor data
    speed = data.iloc[i]["speed"]

    # Magnetometer-based heading
    mag_x = data.iloc[i]["mag_x"]
    mag_y = data.iloc[i]["mag_y"]

    heading = math.atan2(mag_y, mag_x)

    # Distance travelled
    distance = speed * dt

    # North/South movement
    delta_lat = (
        distance * math.cos(heading)
    ) / EARTH_RADIUS

    # East/West movement
    delta_lon = (
        distance * math.sin(heading)
    ) / (
        EARTH_RADIUS *
        math.cos(math.radians(estimated_lat))
    )

    # Update position
    estimated_lat += math.degrees(delta_lat)
    estimated_lon += math.degrees(delta_lon)

    estimated_positions.append(
        [estimated_lat, estimated_lon]
    )

# Add estimated position to dataframe
data["estimated_latitude"] = [
    position[0] for position in estimated_positions
]

data["estimated_longitude"] = [
    position[1] for position in estimated_positions
]

print("\n===== DEAD RECKONING RESULTS =====")

print(
    data[
        [
            "timestamp",
            "latitude",
            "longitude",
            "estimated_latitude",
            "estimated_longitude",
            "speed"
        ]
    ]
)