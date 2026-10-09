import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from PIL import Image, ExifTags
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import io
import math

st.set_page_config(
    page_title="NAVI-DR | Intelligent Navigation",
    page_icon="🛰️",
    layout="wide"
)

st.title("🛰️ NAVI-DR")
st.caption("AI-ML Based Intelligent Dead Reckoning System")
st.subheader("📍 Image GPS Metadata & Location Tracking")


# -----------------------------
# Load sensor data
# -----------------------------
@st.cache_data
def load_sensor_data():
    try:
        df = pd.read_csv("sensor_data.csv")
        df.columns = df.columns.str.strip().str.lower()
        return df
    except FileNotFoundError:
        return pd.DataFrame()


data = load_sensor_data()

if data.empty:
    st.warning(
        "sensor_data.csv was not found or contains no data. "
        "Add it to the same repository as app.py."
    )


# -----------------------------
# EXIF GPS extraction
# -----------------------------
def rational_to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return float(value.numerator) / float(value.denominator)


def dms_to_decimal(dms, ref):
    degrees = rational_to_float(dms[0])
    minutes = rational_to_float(dms[1])
    seconds = rational_to_float(dms[2])

    result = degrees + minutes / 60 + seconds / 3600

    if ref in ("S", "W", b"S", b"W"):
        result = -result

    return result


def get_image_gps(uploaded_image):
    try:
        image = Image.open(io.BytesIO(uploaded_image.getvalue()))
        exif = image.getexif()

        if not exif:
            return None

        gps_info = exif.get_ifd(ExifTags.IFD.GPSInfo)

        if not gps_info:
            return None

        gps_names = {
            ExifTags.GPSTAGS.get(key, key): value
            for key, value in gps_info.items()
        }

        lat = gps_names.get("GPSLatitude")
        lat_ref = gps_names.get("GPSLatitudeRef")
        lon = gps_names.get("GPSLongitude")
        lon_ref = gps_names.get("GPSLongitudeRef")

        if lat is None or lon is None or lat_ref is None or lon_ref is None:
            return None

        latitude = dms_to_decimal(lat, lat_ref)
        longitude = dms_to_decimal(lon, lon_ref)

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return None

        return latitude, longitude

    except Exception:
        return None


# -----------------------------
# Reverse geocoding
# -----------------------------
@st.cache_data(ttl=86400, show_spinner=False)
def get_address(latitude, longitude):
    try:
        geolocator = Nominatim(
            user_agent="NAVI-DR-Student-Project"
        )

        reverse = RateLimiter(
            geolocator.reverse,
            min_delay_seconds=1,
            max_retries=1,
            error_wait_seconds=1
        )

        result = reverse(
            (latitude, longitude),
            language="en",
            exactly_one=True,
            timeout=8
        )

        if result:
            return result.address, result.raw.get("address", {})

    except Exception:
        pass

    return None, {}


# -----------------------------
# Upload image
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload an original photo containing GPS metadata",
    type=["jpg", "jpeg", "tif", "tiff"]
)

latitude = None
longitude = None
location_source = None

if uploaded_file is not None:
    st.image(
        uploaded_file,
        caption="Uploaded image",
        width=300
    )

    image_gps = get_image_gps(uploaded_file)

    if image_gps:
        latitude, longitude = image_gps
        location_source = "Image GPS metadata"
        st.success("GPS metadata found in the image!")

    else:
        st.warning("Image GPS metadata not found.")

        if (
            not data.empty
            and "latitude" in data.columns
            and "longitude" in data.columns
        ):
            gps_data = data.copy()

            gps_data["latitude"] = pd.to_numeric(
                gps_data["latitude"], errors="coerce"
            )
            gps_data["longitude"] = pd.to_numeric(
                gps_data["longitude"], errors="coerce"
            )

            gps_data = gps_data.dropna(
                subset=["latitude", "longitude"]
            )

            gps_data = gps_data[
                gps_data["latitude"].between(-90, 90)
                & gps_data["longitude"].between(-180, 180)
                & (
                    (gps_data["latitude"] != 0)
                    | (gps_data["longitude"] != 0)
                )
            ]

            if not gps_data.empty:
                latest = gps_data.iloc[-1]
                latitude = float(latest["latitude"])
                longitude = float(latest["longitude"])
                location_source = "Latest valid sensor/GPS CSV coordinates"

                st.info(
                    "Using the latest valid location from sensor_data.csv. "
                    "This may not be where the photo was taken."
                )

            else:
                st.error("No valid GPS coordinates found in the CSV.")

        else:
            st.error(
                "Latitude/longitude columns are missing from sensor_data.csv."
            )


# -----------------------------
# Display map and address popup
# -----------------------------
if latitude is not None and longitude is not None:
    st.divider()
    st.subheader("🗺️ Detected Location")

    st.write(f"**Source:** {location_source}")
    st.write(f"**Latitude:** {latitude:.6f}")
    st.write(f"**Longitude:** {longitude:.6f}")

    with st.spinner("Finding the nearby place and address..."):
        address, address_parts = get_address(latitude, longitude)

    if address:
        place_name = (
            address_parts.get("neighbourhood")
            or address_parts.get("suburb")
            or address_parts.get("village")
            or address_parts.get("town")
            or address_parts.get("city")
            or address_parts.get("county")
            or "Detected location"
        )

        city = (
            address_parts.get("city")
            or address_parts.get("town")
            or address_parts.get("village")
            or address_parts.get("municipality")
            or "Not available"
        )

        state = address_parts.get("state", "Not available")
        country = address_parts.get("country", "Not available")

    else:
        place_name = "Location name unavailable"
        address = "Address could not be retrieved. Check your internet connection."
        city = "Not available"
        state = "Not available"
        country = "Not available"

    st.markdown(f"### 📍 {place_name}")
    st.write(f"**Full address:** {address}")
    st.write(f"**City/Town:** {city}")
    st.write(f"**State:** {state}")
    st.write(f"**Country:** {country}")

    location_map = folium.Map(
        location=[latitude, longitude],
        zoom_start=17,
        control_scale=True
    )

    popup_html = f"""
    <div style="width:260px; font-family:Arial;">
        <h4>📍 {place_name}</h4>
        <p><b>Address:</b> {address}</p>
        <p><b>Latitude:</b> {latitude:.6f}</p>
        <p><b>Longitude:</b> {longitude:.6f}</p>
    </div>
    """

    folium.Marker(
        location=[latitude, longitude],
        tooltip=f"📍 {place_name} — tap to view address",
        popup=folium.Popup(popup_html, max_width=320),
        icon=folium.Icon(
            color="red",
            icon="map-marker",
            prefix="fa"
        )
    ).add_to(location_map)

    folium.Circle(
        location=[latitude, longitude],
        radius=40,
        color="red",
        fill=True,
        fill_opacity=0.12
    ).add_to(location_map)

    st_folium(
        location_map,
        width=None,
        height=500,
        use_container_width=True,
        key="navi_dr_location_map"
    )

    st.caption(
        "Tap the red location marker to open the address popup. "
        "The circle represents an illustrative 40-metre radius, "
        "not measured GPS accuracy."
    )

    maps_url = (
        f"https://www.google.com/maps/search/?api=1"
        f"&query={latitude},{longitude}"
    )

    st.link_button("Open location in Google Maps", maps_url)


# -----------------------------
# Sensor data
# -----------------------------
st.divider()
st.subheader("📊 Sensor Data")

if not data.empty:
    st.dataframe(data, use_container_width=True)

    numeric_columns = data.select_dtypes(
        include=np.number
    ).columns.tolist()

    if numeric_columns:
        selected_columns = st.multiselect(
            "Choose sensor values to plot",
            options=numeric_columns,
            default=[
                col for col in ["acc_x", "acc_y", "acc_z"]
                if col in numeric_columns
            ]
        )

        if selected_columns:
            st.line_chart(data[selected_columns])

    # -----------------------------
    # Magnetometer heading
    # -----------------------------
    if "mag_x" in data.columns and "mag_y" in data.columns:
        mag_x = pd.to_numeric(data["mag_x"], errors="coerce")
        mag_y = pd.to_numeric(data["mag_y"], errors="coerce")

        valid_heading = mag_x.notna() & mag_y.notna()

        if valid_heading.any():
            last_index = valid_heading[valid_heading].index[-1]
            heading = math.degrees(
                math.atan2(
                    mag_y.loc[last_index],
                    mag_x.loc[last_index]
                )
            )
            heading = (heading + 360) % 360

            st.metric(
                "Latest raw magnetometer heading",
                f"{heading:.1f}°"
            )
            st.caption(
                "This is a basic heading estimate, not a calibrated "
                "compass direction."
            )

    # -----------------------------
    # GPS path
    # -----------------------------
    st.subheader("🛰️ GPS Track")

    if "latitude" in data.columns and "longitude" in data.columns:
        track = data.copy()

        track["latitude"] = pd.to_numeric(
            track["latitude"], errors="coerce"
        )
        track["longitude"] = pd.to_numeric(
            track["longitude"], errors="coerce"
        )

        track = track.dropna(subset=["latitude", "longitude"])

        track = track[
            track["latitude"].between(-90, 90)
            & track["longitude"].between(-180, 180)
            & (
                (track["latitude"] != 0)
                | (track["longitude"] != 0)
            )
        ]

        if not track.empty:
            st.map(
                track[["latitude", "longitude"]],
                use_container_width=True
            )
        else:
            st.info("No valid GPS track points are available.")
    else:
        st.info("CSV needs latitude and longitude columns.")

    # -----------------------------
    # GNSS outage demonstration
    # -----------------------------
    st.subheader("🚦 GNSS Outage Demonstration")

    st.write(
        "Select a section of the dataset to demonstrate a GNSS blackout. "
        "This view masks GPS coordinates during the selected interval; "
        "it does not calculate a validated dead-reckoned trajectory."
    )

    if len(data) >= 2:
        max_start = len(data) - 1

        blackout_start = st.slider(
            "Blackout start row",
            min_value=0,
            max_value=max_start - 1,
            value=0
        )

        blackout_end = st.slider(
            "Blackout end row",
            min_value=blackout_start + 1,
            max_value=max_start,
            value=min(10, max_start)
        )

        st.write(
            f"GNSS unavailable in rows {blackout_start} "
            f"through {blackout_end}."
        )

        if "latitude" in data.columns and "longitude" in data.columns:
            demo = data.copy()
            demo["latitude"] = pd.to_numeric(
                demo["latitude"], errors="coerce"
            )
            demo["longitude"] = pd.to_numeric(
                demo["longitude"], errors="coerce"
            )

            demo.loc[
                blackout_start:blackout_end,
                ["latitude", "longitude"]
            ] = np.nan

            st.line_chart(
                demo[["latitude", "longitude"]]
            )

            st.caption(
                "This is a GNSS data-masking demonstration only. "
                "IMU-based dead reckoning and drift correction require "
                "a separate validated algorithm."
            )
else:
    st.info(
        "Upload sensor_data.csv to display sensor readings, GPS track, "
        "and the outage demonstration."
    )

st.divider()
st.caption("NAVI-DR | INETIA X | SIH26168")
