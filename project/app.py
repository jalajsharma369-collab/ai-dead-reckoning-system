import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
import os

from PIL import Image, ExifTags
from geopy.geocoders import Nominatim


# =========================================================
# PAGE SETTINGS
# =========================================================

st.set_page_config(
    page_title="Intelligent Dead Reckoning",
    page_icon="🛰️",
    layout="wide"
)


# =========================================================
# TITLE
# =========================================================

st.title("🛰️ AI-ML Based Intelligent Dead Reckoning System")

st.write(
    "Seamless Navigation Prototype using GPS and IMU Sensor Data"
)


# =========================================================
# LOAD SENSOR CSV
# =========================================================

try:

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


# =========================================================
# IMAGE GPS METADATA FUNCTION
# =========================================================

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

        if latitude is None or longitude is None:
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


# =========================================================
# REVERSE GEOCODING
# =========================================================

def get_place_name(latitude, longitude):

    try:

        geolocator = Nominatim(
            user_agent="sih_intelligent_dead_reckoning"
        )

        location = geolocator.reverse(
            f"{latitude}, {longitude}",
            language="en",
            addressdetails=True,
            zoom=18,
            timeout=10
        )

        if location is None:
            return None

        address = location.raw.get("address", {})

        # Try to get the most useful locality
        locality = (
            address.get("suburb")
            or address.get("neighbourhood")
            or address.get("quarter")
            or address.get("residential")
            or address.get("village")
            or address.get("town")
            or address.get("city")
        )

        city = (
            address.get("city")
            or address.get("town")
            or address.get("municipality")
            or address.get("village")
        )

        state = address.get("state")

        country = address.get("country")

        return {
            "locality": locality,
            "city": city,
            "state": state,
            "country": country,
            "full_address": location.address
        }

    except Exception:

        return None


# =========================================================
# IMAGE BASED LOCATION
# =========================================================

st.subheader("📷 Image-Based Location")

st.write(
    "Upload an original camera photo. "
    "The system first checks GPS metadata and then "
    "converts coordinates into a readable place name."
)


uploaded_image = st.file_uploader(
    "Upload an image",
    type=["jpg", "jpeg", "png"]
)


if uploaded_image is not None:

    # -----------------------------------------------------
    # SHOW IMAGE
    # -----------------------------------------------------

    st.image(
        uploaded_image,
        caption="Uploaded Image",
        use_container_width=True
    )

    # -----------------------------------------------------
    # GET GPS FROM IMAGE
    # -----------------------------------------------------

    location = get_gps_from_image(
        uploaded_image
    )

    if location:

        # =================================================
        # IMAGE GPS FOUND
        # =================================================

        image_latitude, image_longitude = location

        location_source = "Image GPS Metadata"

        st.success(
            "📍 GPS metadata successfully detected!"
        )

    else:

        # =================================================
        # FALLBACK TO SENSOR DATA
        # =================================================

        image_latitude = float(
            data["latitude"].iloc[-1]
        )

        image_longitude = float(
            data["longitude"].iloc[-1]
        )

        location_source = "Sensor Data Fallback"

        st.warning(
            "⚠️ Image GPS metadata not found."
        )

        st.info(
            "📍 Using latest available sensor/GPS "
            "location as fallback."
        )

    # -----------------------------------------------------
    # REVERSE GEOCODING
    # -----------------------------------------------------

    place = get_place_name(
        image_latitude,
        image_longitude
    )

    # -----------------------------------------------------
    # DETECTED LOCATION
    # -----------------------------------------------------

    st.subheader("📍 Detected Location")

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Latitude",
            f"{image_latitude:.6f}"
        )

    with col2:

        st.metric(
            "Longitude",
            f"{image_longitude:.6f}"
        )

    # -----------------------------------------------------
    # PLACE NAME
    # -----------------------------------------------------

    if place:

        locality = place.get("locality")
        city = place.get("city")
        state = place.get("state")
        country = place.get("country")

        if locality:

            st.success(
                f"📍 Place: {locality}"
            )

        elif city:

            st.success(
                f"📍 Place: {city}"
            )

        if city:
            st.write(f"🏙️ **City:** {city}")

        if state:
            st.write(f"🗺️ **State:** {state}")

        if country:
            st.write(f"🌍 **Country:** {country}")

        st.caption(
            f"📌 Location Source: {location_source}"
        )

        with st.expander("View full address"):

            st.write(
                place["full_address"]
            )

    else:

        st.info(
            "📍 Coordinates found, but place name "
            "could not be retrieved."
        )

    # -----------------------------------------------------
    # MAP
    # -----------------------------------------------------

    st.subheader("🗺️ Location Map")

    image_map = pd.DataFrame(
        {
            "lat": [image_latitude],
            "lon": [image_longitude]
        }
    )

    st.map(
        image_map,
        latitude="lat",
        longitude="lon",
        zoom=15
    )


# =========================================================
# SENSOR DATA
# =========================================================

st.subheader("📊 Sensor Data")

st.dataframe(
    data,
    use_container_width=True
)


# =========================================================
# CALCULATE HEADING
# =========================================================

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


# =========================================================
# CURRENT NAVIGATION STATUS
# =========================================================

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


# =========================================================
# IMU SENSOR INFORMATION
# =========================================================

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


# =========================================================
# GPS NAVIGATION PATH
# =========================================================

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


# =========================================================
# GPS OUTAGE SIMULATION
# =========================================================

st.subheader("🚨 GPS Outage Simulation")

st.info(
    "During GPS outage, the system can use "
    "accelerometer, gyroscope, magnetometer, "
    "speed and previous position to estimate movement."
)


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "SIH Prototype | Python | Streamlit | Pandas | Plotly | GeoPy"
)
