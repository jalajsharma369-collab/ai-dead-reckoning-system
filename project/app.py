import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from PIL import Image, ExifTags
from io import BytesIO

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="NAVI-DR | Dead Reckoning",
    page_icon="🧭",
    layout="wide"
)

st.title("🧭 NAVI-DR")
st.subheader("AI-ML Based Intelligent Dead Reckoning System")
st.caption("Offline sensor-data demonstration")

# =====================================================
# LOAD SENSOR DATA
# =====================================================
@st.cache_data
def load_data(file_bytes):
    from io import BytesIO
    return pd.read_csv(BytesIO(file_bytes))


st.sidebar.header("Sensor Dataset")

uploaded_csv = st.sidebar.file_uploader(
    "Upload sensor_data.csv (optional)",
    type=["csv"]
)

data = None

try:
    if uploaded_csv is not None:
        data = load_data(uploaded_csv.getvalue())
    else:
        # Reads sensor_data.csv from the same folder as app.py
        data = pd.read_csv("sensor_data.csv")

except FileNotFoundError:
    st.warning(
        "sensor_data.csv was not found. Upload your existing CSV "
        "using the sidebar."
    )
except Exception as error:
    st.error(f"Could not load the CSV: {error}")

# =====================================================
# PHOTO UPLOAD
# =====================================================
st.divider()
st.header("📷 Photo Viewer")

photo = st.file_uploader(
    "Upload a photo (optional)",
    type=["jpg", "jpeg", "tif", "tiff"]
)

if photo is not None:
    try:
        with Image.open(BytesIO(photo.getvalue())) as img:
            st.image(
                img.copy(),
                caption="Uploaded photo",
                use_container_width=True
            )

        st.info(
            "A photo's exact location cannot be determined from "
            "sensor_data.csv alone. The photo needs its own GPS "
            "metadata or another reliable location reference."
        )

        try:
            with Image.open(BytesIO(photo.getvalue())) as img:
                exif = img.getexif()
                gps = exif.get_ifd(ExifTags.IFD.GPSInfo) if exif else {}

            if gps:
                st.success("GPS metadata exists in the photo.")
                st.caption(
                    "The metadata is present. This viewer does not "
                    "automatically infer the photo location from it."
                )
            else:
                st.warning(
                    "No readable GPS metadata found in this photo."
                )

        except Exception:
            st.warning("Could not read GPS metadata from this photo.")

    except Exception:
        st.error("Could not open the photo. Try an original JPG file.")

# =====================================================
# SENSOR DATA ANALYSIS
# =====================================================
st.divider()
st.header("📊 Sensor Data Analysis")

if data is not None:
    if data.empty:
        st.warning("The sensor CSV contains no rows.")
    else:
        st.success(f"Loaded {len(data)} sensor records.")

        # Convert common sensor columns to numbers
        numeric_columns = [
            "timestamp",
            "acc_x", "acc_y", "acc_z",
            "gyro_x", "gyro_y", "gyro_z",
            "mag_x", "mag_y", "mag_z",
            "latitude", "longitude", "speed"
        ]

        for column in numeric_columns:
            if column in data.columns:
                data[column] = pd.to_numeric(
                    data[column], errors="coerce"
                )

        st.subheader("Data Preview")
        st.dataframe(data.head(30), use_container_width=True)

        # ---------------------------------------------
        # ACCELEROMETER
        # ---------------------------------------------
        acc_cols = [
            c for c in ["acc_x", "acc_y", "acc_z"]
            if c in data.columns
        ]

        if acc_cols:
            st.subheader("📈 Accelerometer")
            st.line_chart(data[acc_cols])

        # ---------------------------------------------
        # GYROSCOPE
        # ---------------------------------------------
        gyro_cols = [
            c for c in ["gyro_x", "gyro_y", "gyro_z"]
            if c in data.columns
        ]

        if gyro_cols:
            st.subheader("🔄 Gyroscope")
            st.line_chart(data[gyro_cols])

        # ---------------------------------------------
        # MAGNETOMETER
        # ---------------------------------------------
        mag_cols = [
            c for c in ["mag_x", "mag_y", "mag_z"]
            if c in data.columns
        ]

        if mag_cols:
            st.subheader("🧲 Magnetometer")
            st.line_chart(data[mag_cols])

        # ---------------------------------------------
        # RECORDED GPS ROUTE
        # ---------------------------------------------
        st.divider()
        st.header("🗺️ Recorded GPS Route")

        if {"latitude", "longitude"}.issubset(data.columns):
            gps_data = data.dropna(
                subset=["latitude", "longitude"]
            ).copy()

            gps_data = gps_data[
                gps_data["latitude"].between(-90, 90)
                & gps_data["longitude"].between(-180, 180)
            ]

            if not gps_data.empty:
                points = gps_data[
                    ["latitude", "longitude"]
                ].values.tolist()

                route_map = folium.Map(
                    location=points[0],
                    zoom_start=14,
                    control_scale=True
                )

                if len(points) > 1:
                    folium.PolyLine(
                        points,
                        color="blue",
                        weight=4,
                        tooltip="Recorded sensor GPS route"
                    ).add_to(route_map)

                folium.Marker(
                    points[0],
                    tooltip="First recorded point",
                    icon=folium.Icon(color="green")
                ).add_to(route_map)

                folium.Marker(
                    points[-1],
                    tooltip="Last recorded point",
                    icon=folium.Icon(color="red")
                ).add_to(route_map)

                st_folium(
                    route_map,
                    use_container_width=True,
                    height=420,
                    key="recorded_route_map"
                )

                st.caption(
                    "This is the route saved in your CSV. It does not "
                    "represent the phone's current location."
                )
            else:
                st.warning(
                    "Latitude and longitude columns exist, but "
                    "no valid recorded coordinates were found."
                )
        else:
            st.info(
                "No latitude/longitude columns found. Sensor charts "
                "can still work, but a recorded GPS route cannot be shown."
            )

        # ---------------------------------------------
        # SIMULATED GPS BLACKOUT
        # ---------------------------------------------
        st.divider()
        st.header("🛰️ GPS Blackout Simulation")

        st.write(
            "Temporarily hide recorded GPS coordinates in the first "
            "part of the dataset. This simulates a GPS outage while "
            "preserving the sensor readings."
        )

        if {"latitude", "longitude"}.issubset(data.columns):
            blackout_percent = st.slider(
                "Rows affected by simulated GPS outage (%)",
                min_value=10,
                max_value=90,
                value=30,
                step=10
            )

            demo = data.copy()
            count = int(len(demo) * blackout_percent / 100)

            if count > 0:
                demo.loc[
                    demo.index[:count],
                    ["latitude", "longitude"]
                ] = np.nan

            st.write("Dataset with simulated GPS outage:")
            st.dataframe(demo.head(50), use_container_width=True)

            st.caption(
                "This is only a simulation of missing GPS values. "
                "It does not calculate replacement positions."
            )
        else:
            st.info(
                "Blackout masking requires latitude and longitude "
                "columns. IMU sensor analysis remains available."
            )

        # ---------------------------------------------
        # BASIC IMU MOVEMENT INDICATOR
        # ---------------------------------------------
        st.divider()
        st.header("🧭 IMU Activity Indicator")

        required_acc = {"acc_x", "acc_y", "acc_z"}

        if required_acc.issubset(data.columns):
            activity = data[
                ["acc_x", "acc_y", "acc_z"]
            ].copy()

            activity = activity.dropna()

            if not activity.empty:
                activity["acc_magnitude"] = np.sqrt(
                    activity["acc_x"] ** 2
                    + activity["acc_y"] ** 2
                    + activity["acc_z"] ** 2
                )

                st.line_chart(activity[["acc_magnitude"]])

                st.caption(
                    "This shows acceleration magnitude from recorded "
                    "sensor data. It is not a position or distance estimate."
                )
            else:
                st.warning(
                    "No valid accelerometer readings are available."
                )
        else:
            st.info(
                "For the activity indicator, the CSV needs acc_x, "
                "acc_y and acc_z columns."
            )

# =====================================================
# FOOTER
# =====================================================
st.divider()
st.caption(
    "NAVI-DR | Recorded data can be analysed without current phone GPS. "
    "Actual dead-reckoning position estimation requires a suitable "
    "motion model, sampling intervals, initial conditions and drift handling."
)
