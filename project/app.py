import streamlit as st
import pandas as pd
import numpy as np
import folium

from PIL import Image, ExifTags
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from io import BytesIO

# ==================================================
# PAGE CONFIGURATION
# ==================================================
st.set_page_config(
    page_title="NAVI-DR | Intelligent Dead Reckoning",
    page_icon="🧭",
    layout="wide"
)

st.title("🧭 NAVI-DR")
st.subheader("AI-ML Based Intelligent Dead Reckoning System")
st.write(
    "AI-ML based Intelligent Dead Reckoning system "
    "for seamless navigation."
)

# ==================================================
# PHOTO GPS FUNCTIONS
# ==================================================
def rational_to_float(value):
    """Convert an EXIF rational value into a float."""
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        if value.denominator == 0:
            raise ValueError("Invalid rational number")
        return float(value.numerator) / float(value.denominator)
    return float(value)


def dms_to_decimal(value):
    """Convert GPS degrees, minutes and seconds to decimal."""
    if value is None or len(value) < 3:
        return None

    degrees = rational_to_float(value[0])
    minutes = rational_to_float(value[1])
    seconds = rational_to_float(value[2])

    return degrees + minutes / 60.0 + seconds / 3600.0


def get_image_gps(uploaded_file):
    """
    Return (latitude, longitude) if the image contains readable
    EXIF GPS coordinates. Otherwise return None.
    """
    try:
        with Image.open(BytesIO(uploaded_file.getvalue())) as image:
            exif = image.getexif()

            if not exif:
                return None

            gps_info = {}

            # Preferred method in current Pillow versions
            try:
                gps_info = exif.get_ifd(ExifTags.IFD.GPSInfo)
            except (AttributeError, KeyError, TypeError, ValueError):
                gps_info = {}

            # Compatibility fallback for some older image metadata
            if not gps_info:
                raw_gps = exif.get(34853)

                if isinstance(raw_gps, dict):
                    gps_info = raw_gps

            # Convert numeric EXIF tag IDs to readable names
            readable = {}

            for tag_id, value in gps_info.items():
                name = ExifTags.GPSTAGS.get(tag_id, tag_id)
                readable[name] = value

            # Accept already-readable GPS names too
            readable.update({
                key: value
                for key, value in gps_info.items()
                if isinstance(key, str)
            })

            lat_value = readable.get("GPSLatitude")
            lon_value = readable.get("GPSLongitude")
            lat_ref = readable.get("GPSLatitudeRef")
            lon_ref = readable.get("GPSLongitudeRef")

            if lat_value is None or lon_value is None:
                return None

            latitude = dms_to_decimal(lat_value)
            longitude = dms_to_decimal(lon_value)

            if latitude is None or longitude is None:
                return None

            if str(lat_ref).upper().startswith("S"):
                latitude = -latitude

            if str(lon_ref).upper().startswith("W"):
                longitude = -longitude

            if not (-90 <= latitude <= 90):
                return None

            if not (-180 <= longitude <= 180):
                return None

            return latitude, longitude

    except Exception:
        return None


# ==================================================
# PHOTO UPLOAD
# ==================================================
st.divider()
st.header("📷 Photo GPS Location")

uploaded_file = st.file_uploader(
    "Upload the original photo",
    type=["jpg", "jpeg", "tif", "tiff"]
)

if uploaded_file is not None:
    try:
        with Image.open(BytesIO(uploaded_file.getvalue())) as image:
            st.image(
                image.copy(),
                caption="Uploaded photo",
                use_container_width=True
            )

        gps_result = get_image_gps(uploaded_file)

        if gps_result is None:
            st.warning(
                "GPS metadata not found. This image does not contain "
                "readable GPS coordinates."
            )

            st.info(
                "For a new photo, enable Location on your phone and "
                "turn on location tagging in the Camera settings. "
                "Take a new photo and upload the original file."
            )

            st.caption(
                "The app will not guess the photo location or use "
                "sensor_data.csv as a replacement."
            )

        else:
            latitude, longitude = gps_result

            st.success("GPS coordinates found in photo metadata.")

            col1, col2 = st.columns(2)
            col1.metric("Latitude", f"{latitude:.6f}")
            col2.metric("Longitude", f"{longitude:.6f}")

            maps_url = (
                f"https://www.google.com/maps"
                f"?q={latitude},{longitude}"
            )

            st.markdown(
                f"[Open photo coordinates in Google Maps]({maps_url})"
            )

            # Reverse geocoding is optional
            try:
                geolocator = Nominatim(
                    user_agent="navi_dr_student_project"
                )

                location = geolocator.reverse(
                    (latitude, longitude),
                    exactly_one=True,
                    timeout=10
                )

                if location:
                    st.write("**Mapped address:**", location.address)
                else:
                    st.caption("No address was returned for these coordinates.")

            except Exception:
                st.caption(
                    "Address lookup is unavailable, but the GPS "
                    "coordinates can still be displayed."
                )

            # Photo GPS map
            photo_map = folium.Map(
                location=[latitude, longitude],
                zoom_start=17,
                control_scale=True
            )

            folium.Marker(
                location=[latitude, longitude],
                tooltip="Photo GPS location",
                popup=(
                    f"Latitude: {latitude:.6f}<br>"
                    f"Longitude: {longitude:.6f}"
                ),
                icon=folium.Icon(
                    color="red",
                    icon="camera",
                    prefix="fa"
                )
            ).add_to(photo_map)

            st.subheader("📍 Photo Location Map")

            st_folium(
                photo_map,
                height=450,
                use_container_width=True,
                key="photo_map"
            )

    except Exception as error:
        st.error(
            "Unable to open this image. Please upload a valid JPG or TIFF."
        )
        st.caption(f"Details: {error}")


# ==================================================
# SENSOR DATA
# ==================================================
st.divider()
st.header("📊 Sensor Data Analysis")


@st.cache_data
def load_sensor_data():
    return pd.read_csv("sensor_data.csv")


try:
    data = load_sensor_data()

    st.success("Sensor data loaded successfully.")

    # Convert expected numeric columns
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
                data[column],
                errors="coerce"
            )

    st.subheader("Sensor Data Preview")
    st.dataframe(data.head(20), use_container_width=True)

    # Acceleration
    acc_columns = [
        column
        for column in ["acc_x", "acc_y", "acc_z"]
        if column in data.columns
    ]

    if acc_columns:
        st.subheader("Acceleration")
        st.line_chart(data[acc_columns])

    # Gyroscope
    gyro_columns = [
        column
        for column in ["gyro_x", "gyro_y", "gyro_z"]
        if column in data.columns
    ]

    if gyro_columns:
        st.subheader("Gyroscope")
        st.line_chart(data[gyro_columns])

    # Magnetometer
    mag_columns = [
        column
        for column in ["mag_x", "mag_y", "mag_z"]
        if column in data.columns
    ]

    if mag_columns:
        st.subheader("Magnetometer")
        st.line_chart(data[mag_columns])

    # ==================================================
    # SENSOR GPS TRACK - NOT THE PHOTO LOCATION
    # ==================================================
    st.subheader("🛰️ Sensor Dataset GPS Track")

    if {"latitude", "longitude"}.issubset(data.columns):
        track = data.dropna(
            subset=["latitude", "longitude"]
        ).copy()

        track = track[
            track["latitude"].between(-90, 90)
            & track["longitude"].between(-180, 180)
        ]

        if not track.empty:
            points = track[
                ["latitude", "longitude"]
            ].values.tolist()

            track_map = folium.Map(
                location=points[0],
                zoom_start=14,
                control_scale=True
            )

            if len(points) > 1:
                folium.PolyLine(
                    points,
                    color="blue",
                    weight=4,
                    tooltip="Sensor GPS track"
                ).add_to(track_map)

            folium.Marker(
                points[0],
                tooltip="Track start",
                icon=folium.Icon(color="green")
            ).add_to(track_map)

            folium.Marker(
                points[-1],
                tooltip="Track end",
                icon=folium.Icon(color="blue")
            ).add_to(track_map)

            st_folium(
                track_map,
                height=400,
                use_container_width=True,
                key="sensor_track_map"
            )

            st.caption(
                "This map shows the sensor CSV coordinates, "
                "not the uploaded photo's location."
            )

        else:
            st.info(
                "No valid GPS coordinates found in sensor_data.csv."
            )

    else:
        st.info(
            "The sensor CSV needs latitude and longitude columns "
            "to display a GPS track."
        )

    # ==================================================
    # GNSS BLACKOUT DEMONSTRATION
    # ==================================================
    st.divider()
    st.subheader("GNSS Blackout Demonstration")

    if {"latitude", "longitude"}.issubset(data.columns):
        blackout_percent = st.slider(
            "Percentage of initial rows to mask",
            min_value=5,
            max_value=80,
            value=30,
            step=5
        )

        demo_data = data.copy()
        rows_to_mask = int(
            len(demo_data) * blackout_percent / 100
        )

        if rows_to_mask > 0:
            demo_data.iloc[
                :rows_to_mask,
                demo_data.columns.get_indexer(
                    ["latitude", "longitude"]
                )
            ] = np.nan

        st.dataframe(
            demo_data.head(20),
            use_container_width=True
        )

        st.caption(
            "Demonstration only: GNSS coordinates are masked in selected "
            "rows. This does not itself calculate dead-reckoning positions "
            "or verify the project's accuracy target."
        )

    else:
        st.info(
            "GNSS blackout demonstration requires latitude and "
            "longitude columns in sensor_data.csv."
        )

except FileNotFoundError:
    st.error(
        "sensor_data.csv not found. Place it in the same folder as app.py."
    )

except pd.errors.EmptyDataError:
    st.error("sensor_data.csv is empty.")

except Exception as error:
    st.error("An error occurred while processing sensor data.")
    st.caption(f"Details: {error}")


# ==================================================
# FOOTER
# ==================================================
st.divider()

st.caption(
    "NAVI-DR | Student prototype | Photo GPS metadata and sensor "
    "dataset coordinates are handled separately."
)
