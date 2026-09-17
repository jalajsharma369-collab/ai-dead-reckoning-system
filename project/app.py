import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import os

from PIL import Image, ExifTags


# -----------------------------
# PAGE SETTINGS
# -----------------------------

st.set_page_config(
    page_title="Intelligent Dead Reckoning",
    page_icon="🛰️",
    layout="wide"
)


# -----------------------------
# TITLE
# -----------------------------

st.title("🛰️ AI-ML Based Intelligent Dead Reckoning System")

st.write(
    "Seamless Navigation Prototype using GPS and IMU Sensor Data"
)


# -----------------------------
# IMAGE BASED LOCATION
# -----------------------------

st.subheader("📷 Image-Based Location")

st.write(
    "Upload a photo containing GPS metadata to extract its location."
)

uploaded_image = st.file_uploader(
    "Upload an image",
    type=["jpg", "jpeg", "png"]
)


def get_gps_from_image(uploaded_file):

    try:

        image = Image.open(uploaded_file)

        exif = image.getexif()

        if not exif:
            return None

        gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)

        if not gps_ifd:
            return None

        gps = {
            ExifTags.GPSTAGS.get(key, key): value
            for key, value in gps_ifd.items()
        }

        latitude = gps.get("GPSLatitude")
        latitude_ref = gps.get("GPSLatitudeRef")

        longitude = gps.get("GPSLongitude")
        longitude_ref = gps.get("GPSLongitudeRef")

        if not latitude or not longitude:
            return None

        def convert_to_decimal(value, ref):

            degrees = float(value[0])
            minutes = float(value[1])
            seconds = float(value[2])

            decimal = (
                degrees
                + minutes / 60
                + seconds / 3600
            )

            if ref in ["S", "W"]:
                decimal = -decimal

            return decimal

        lat = convert_to_decimal(
            latitude,
            latitude_ref
        )

        lon = convert_to_decimal(
            longitude,
            longitude_ref
        )

        return lat, lon

    except Exception:

        return None


if uploaded_image:

    st.image(
        uploaded_image,
        caption="Uploaded Image",
        use_container_width=True
    )

    location = get_gps_from_image(uploaded_image)

    if location:

        image_latitude, image_longitude = location

        st.success("📍 GPS location found in image!")

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Image Latitude",
                f"{image_latitude:.6f}"
            )

        with col2:

            st.metric(
                "Image Longitude",
                f"{image_longitude:.6f}"
            )

        image_map = pd.DataFrame(
            {
                "lat": [image_latitude],
                "lon": [image_longitude]
            }
        )

        st.map(image_map)

    else:

        st.warning(
            "⚠️ No GPS location metadata was found in this image."
        )

        st.info(
            "Try uploading an original photo taken with a phone "
            "camera that has location services enabled."
        )


# -----------------------------
# LOAD CSV DATA
# -----------------------------

try:

    # Find sensor_data.csv in the same folder as app.py
    app_folder = os.path.dirname(os.path.abspath(__file__))

    csv_path = os.path.join(
        app_folder,
        "sensor_data.csv"
    )

    data = pd.read_csv(csv_path)

    st.success("✅ Sensor data loaded successfully!")

except FileNotFoundError:

    st.error(
        "❌ sensor_data.csv not found. "
        "Please keep sensor_data.csv inside the project folder."
    )

    st.stop()


# -----------------------------
# SHOW DATA
# -----------------------------

st.subheader("📊 Sensor Data")

st.dataframe(
    data,
    use_container_width=True
)


# -----------------------------
# CALCULATE HEADING
# -----------------------------

def calculate_heading(mx, my):

    heading = math.degrees(
        math.atan2(my, mx)
    )

    if heading < 0:
        heading += 360

    return heading


data["heading"] = data.apply(
    lambda row: calculate_heading(
        row["mag_x"],
        row["mag_y"]
    ),
    axis=1
)


# -----------------------------
# CURRENT VALUES
# -----------------------------

latest = data.iloc[-1]

st.subheader("📡 Current Navigation Status")

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Latitude",
        f"{latest['latitude']:.6f}"
    )

with col2:

    st.metric(
        "Longitude",
        f"{latest['longitude']:.6f}"
    )

with col3:

    st.metric(
        "Speed",
        f"{latest['speed']:.2f} m/s"
    )

with col4:

    st.metric(
        "Heading",
        f"{latest['heading']:.1f}°"
    )


# -----------------------------
# SENSOR INFORMATION
# -----------------------------

st.subheader("📱 IMU Sensor Information")

col1, col2, col3 = st.columns(3)

with col1:

    st.write("### 🚶 Accelerometer")

    st.write("X:", latest["acc_x"])
    st.write("Y:", latest["acc_y"])
    st.write("Z:", latest["acc_z"])

with col2:

    st.write("### 🔄 Gyroscope")

    st.write("X:", latest["gyro_x"])
    st.write("Y:", latest["gyro_y"])
    st.write("Z:", latest["gyro_z"])

with col3:

    st.write("### 🧭 Magnetometer")

    st.write("X:", latest["mag_x"])
    st.write("Y:", latest["mag_y"])
    st.write("Z:", latest["mag_z"])


# -----------------------------
# GPS PATH
# -----------------------------

st.subheader("🗺️ GPS Navigation Path")

fig = go.Figure()

fig.add_trace(
    go.Scattermap(
        lat=data["latitude"],
        lon=data["longitude"],
        mode="lines+markers",
        name="GPS Path"
    )
)

fig.update_layout(

    map=dict(
        style="open-street-map",

        center=dict(
            lat=data["latitude"].mean(),
            lon=data["longitude"].mean()
        ),

        zoom=15
    ),

    height=500,

    margin=dict(
        l=0,
        r=0,
        t=0,
        b=0
    )
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# -----------------------------
# GPS OUTAGE
# -----------------------------

st.subheader("🚨 GPS Outage Simulation")

st.info(
    "During GPS outage, the system can use "
    "accelerometer, gyroscope, magnetometer, "
    "speed and previous position to estimate movement."
)


# -----------------------------
# FOOTER
# -----------------------------

st.markdown("---")

st.caption(
    "SIH Prototype | Python | Streamlit | Pandas | Plotly"
)
