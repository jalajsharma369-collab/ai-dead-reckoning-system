import streamlit as st
import pandas as pd
import numpy as np
import folium

from PIL import Image, ExifTags
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError
from io import BytesIO
import math

# --------------------------------------------------
# PAGE SETTINGS
# --------------------------------------------------
st.set_page_config(
    page_title="NAVI-DR | Intelligent Dead Reckoning",
    page_icon="🧭",
    layout="wide"
)

st.title("🧭 NAVI-DR")
st.subheader("AI-ML Based Intelligent Dead Reckoning System")
st.write(
    "Upload a photo to check whether it contains GPS metadata. "
    "Sensor data and photo location are handled separately."
)

# --------------------------------------------------
# GPS / EXIF HELPERS
# --------------------------------------------------
def convert_coordinate(value):
    """Convert EXIF degrees/minutes/seconds to decimal degrees."""
    try:
        parts = list(value)

        def rational_to_float(item):
            if hasattr(item, "numerator") and hasattr(item, "denominator"):
                if item.denominator == 0:
                    raise ValueError("Invalid EXIF rational value")
                return float(item.numerator) / float(item.denominator)
            return float(item)

        degrees = rational_to_float(parts[0])
        minutes = rational_to_float(parts[1])
        seconds = rational_to_float(parts[2])

        return degrees + minutes / 60 + seconds / 3600
    except (TypeError, ValueError, IndexError, ZeroDivisionError):
        return None


def get_image_gps(uploaded_file):
    """
    Return (latitude, longitude) only when valid GPS coordinates
    exist in the uploaded image's EXIF metadata.
    Otherwise return None.
    """
    try:
        image_bytes = uploaded_file.getvalue()

        with Image.open(BytesIO(image_bytes)) as image:
            exif = image.getexif()

            if not exif:
                return None

            # Modern Pillow method
            gps_info = {}
            try:
                gps_info = exif.get_ifd(ExifTags.IFD.GPSInfo)
            except (AttributeError, KeyError, TypeError, ValueError):
                pass

            # Compatibility fallback for images/Pillow versions
            if not gps_info:
                raw_gps = exif.get(34853)
                if isinstance(raw_gps, dict):
                    gps_info = raw_gps

            # Convert numeric EXIF tag IDs to readable names
            named_gps = {}
            for tag_id, value in gps_info.items():
                tag_name = ExifTags.GPSTAGS.get(tag_id, tag_id)
                named_gps[tag_name] = value

            # Some files already provide readable GPS tag names
            if "GPSLatitude" not in named_gps:
                named_gps.update(gps_info)

            lat_value = named_gps.get("GPSLatitude")
            lon_value = named_gps.get("GPSLongitude")
            lat_ref = named_gps.get("GPSLatitudeRef")
            lon_ref = named_gps.get("GPSLongitudeRef")

            if lat_value is None or lon_value is None:
                return None

            latitude = convert_coordinate(lat_value)
            longitude = convert_coordinate(lon_value)

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


# --------------------------------------------------
# PHOTO UPLOAD AND LOCATION
# --------------------------------------------------
st.header("📷 Photo Location Detection")

uploaded_file = st.file_uploader(
    "Upload the original photo",
    type=["jpg", "jpeg", "tif", "tiff"]
)

if uploaded_file is not None:
    try:
        image_bytes = uploaded_file.getvalue()

        with Image.open(BytesIO(image_bytes)) as image:
            st.image(
                image.copy(),
                caption="Uploaded photo",
                use_container_width=True
            )

        gps_result = get_image_gps(uploaded_file)

        if gps_result is None:
            st.warning(
                "GPS metadata not found in this photo. "
                "The exact photo location cannot be determined from "
                "this image's available GPS metadata."
            )

            st.markdown(
                """
                **Try these steps:**
                1. On your phone, turn on Location.
                2. Open Camera settings and enable location tagging.
                3. Take a new photo using the phone's Camera app.
                4. Upload the original JPG file directly, not a
                   screenshot or a copy downloaded from a messaging app.
                """
            )

            st.info(
                "The app will not substitute sensor_data.csv coordinates "
                "because those coordinates may be from a different place."
            )

        else:
            latitude, longitude = gps_result

            st.success("GPS coordinates found in the photo metadata.")

            col1, col2 = st.columns(2)
            col1.metric("Latitude", f"{latitude:.6f}")
            col2.metric("Longitude", f"{longitude:.6f}")

            st.markdown(
                f"[Open coordinates in Google Maps]"
                f"(https://www.google.com/maps?q={latitude},{longitude})"
            )

            # Reverse geocoding: convert coordinates to an address
            address = None
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
                    address = location.address
            except (GeocoderServiceError, TimeoutError, OSError):
                address = None
            except Exception:
                address = None

            if address:
                st.write("**Approximate mapped address:**", address)
            else:
                st.caption(
                    "Address lookup was unavailable. Coordinates are "
                    "still shown on the map."
                )

            # Map using only coordinates from the uploaded photo
            photo_map = folium.Map(
                location=[latitude, longitude],
                zoom_start=17,
                control_scale=True
            )

            folium.Marker(
                [latitude, longitude],
                tooltip="Photo GPS coordinates",
                popup=(
                    f"Latitude: {latitude:.6f}<br>"
                    f"Longitude: {longitude:.6f}"
                ),
                icon=folium.Icon(color="red", icon="camera")
            ).add_to(photo_map)

            st.subheader("📍 Photo GPS Map")
            st_folium(
                photo_map,
                width=None,
                height=450,
                key="photo_location_map"
            )

except Exception as error:
    st.error("Could not read this image. Please try an original JPG photo.")
    st.caption(f"Technical detail: {error}")


# --------------------------------------------------
# SENSOR DATA
# --------------------------------------------------
st.divider()
st.header("📊 Sensor Data Analysis")

@st.cache_data
def load_sensor_data():
    return pd.read_csv("sensor_data.csv")


try:
    data = load_sensor_data()

    st.success("sensor_data.csv loaded successfully.")

    st.subheader("Sensor Data Preview")
    st.dataframe(data.head(20), use_container_width=True)

    # Convert known numeric sensor columns safely
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

    # Acceleration chart
    acceleration_columns = [
        c for c in ["acc_x", "acc_y", "acc_z"] if c in data.columns
    ]

    if acceleration_columns:
        st.subheader("Acceleration")
        st.line_chart(data[acceleration_columns])

    # Gyroscope chart
    gyro_columns = [
        c for c in ["gyro_x", "gyro_y", "gyro_z"] if c in data.columns
    ]

    if gyro_columns:
        st.subheader("Gyroscope")
        st.line_chart(data[gyro_columns])

    # Magnetometer chart
    magnetometer_columns = [
        c for c in ["mag_x", "mag_y", "mag_z"] if c in data.columns
    ]

    if magnetometer_columns:
        st.subheader("Magnetometer")
        st.line_chart(data[magnetometer_columns])

    # Independent sensor GPS track map
    # This map is NOT used as the photo's location.
    if {"latitude", "longitude"}.issubset(data.columns):
        track = data.dropna(subset=["latitude", "longitude"]).copy()

        track = track[
            track["latitude"].between(-90, 90)
            & track["longitude"].between(-180, 180)
        ]

        st.subheader("🛰️ Sensor Dataset GPS Track")

        if not track.empty:
            track_points = track[["latitude", "longitude"]].values.tolist()

            track_map = folium.Map(
                location=track_points[0],
                zoom_start=14,
                control_scale=True
            )

            folium.PolyLine(
                track_points,
                color="blue",
                weight=4,
                tooltip="Sensor dataset GPS track"
            ).add_to(track_map)

            folium.Marker(
                track_points[0],
                tooltip="Track start",
                icon=folium.Icon(color="green")
            ).add_to(track_map)

            folium.Marker(
                track_points[-1],
                tooltip="Track end",
                icon=folium.Icon(color="blue")
            ).add_to(track_map)

            st_folium(
                track_map,
                width=None,
                height=400,
                key="sensor_track_map"
            )
        else:
            st.info(
                "No valid latitude/longitude coordinates found "
                "in sensor_data.csv."
            )

    # Simple GNSS blackout demonstration
    if "latitude" in data.columns and "longitude" in data.columns:
        st.subheader("GNSS Availability Demonstration")

        blackout_fraction = st.slider(
            "Percentage of rows to mask as GNSS blackout",
            min_value=5,
            max_value=80,
            value=30,
            step=5
        )

        demo = data.copy()
        number_to_mask = int(len(demo) * blackout_fraction / 100)

        if number_to_mask > 0:
            demo.loc[
                demo.index[:number_to_mask],
                ["latitude", "longitude"]
            ] = np.nan

        st.caption(
            "Illustration only: this masks some GNSS rows. It does not "
            "calculate or validate dead-reckoning accuracy."
        )

        st.dataframe(demo.head(20), use_container_width=True)

except FileNotFoundError:
    st.error(
        "sensor_data.csv was not found. Put it in the same project "
        "folder as app.py."
    )
except Exception as error:
    st.error("Could not load or process sensor_data.csv.")
    st.caption(f"Technical detail: {error}")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.divider()
st.caption(
    "NAVI-DR | Student prototype. Photo coordinates are shown only "
    "when readable GPS metadata is available. Sensor track coordinates "
    "are displayed separately."
)
