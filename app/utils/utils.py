from datetime import datetime

import numpy as np
import pytz

from app.internal.constants import (
    EARTH_RADIUS_KM,
    SOLAR_IRRADIANCE_CONSTANT_W_m2,
    TIMEZONE,
)


def haversine_distance(
    lat_array: float, lon_array: float, lat: float, lon: float
) -> float:
    R = EARTH_RADIUS_KM
    lat_array, lon_array, lat, lon = map(
        np.radians, [lat_array, lon_array, lat, lon]
    )  # Convert degrees to radians

    dlat = lat - lat_array
    dlon = lon - lon_array

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat_array) * np.cos(lat) * np.sin(dlon / 2.0) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    distance = R * c
    return distance


def extraterrestrial_radiation(
    utc_datetimes: np.ndarray,
    lat: float,
    lon: float,
) -> tuple[np.ndarray, np.ndarray]:
    if type(utc_datetimes[0]) is datetime:
        local_datetimes = [
            dt.replace(second=0, microsecond=0, tzinfo=pytz.utc).astimezone(
                pytz.timezone(TIMEZONE)
            )
            for dt in utc_datetimes
        ]
    else:
        local_datetimes = [
            dt.item()
            .replace(second=0, microsecond=0, tzinfo=pytz.utc)
            .astimezone(pytz.timezone(TIMEZONE))
            for dt in utc_datetimes
        ]

    days_of_year = np.array([dt.timetuple().tm_yday for dt in local_datetimes])
    local_hours = np.array([dt.hour for dt in local_datetimes])
    local_minutes = np.array([dt.minute for dt in local_datetimes])

    Isc = SOLAR_IRRADIANCE_CONSTANT_W_m2

    phi = np.deg2rad(lat)  # Latitude - North Degrees: Input  -90° - 90°
    psi = -1 * lon
    if lon < 0:
        psi = -1 * lon
    elif lon > 0:
        psi = 360 - lon

    psi_std = np.abs(15.0 * np.round(psi / 15.0))

    # J in rad - (pg.9)
    B = 2 * np.pi * (days_of_year - 1) / 365.0

    # Time equation - From Eq 1.5.3 (pg.12) - and its references
    Et = 229.18 * (
        0.000075
        + 0.001868 * np.cos(B)
        - 0.032077 * np.sin(B)
        - 0.014615 * np.cos(2 * B)
        - 0.04089 * np.sin(2 * B)
    )

    # Earth-Sun distance(AU) - From Eq. 1.4.1b (pg.9)
    dr = (
        1.000110
        + 0.034221 * np.cos(B)
        + 0.001280 * np.sin(B)
        + 0.000719 * np.cos(2 * B)
        + 0.000077 * np.sin(2 * B)
    )

    # Daily solar declination (rad) - From Eq. 1.6.1b (pg.14)
    delta = (
        0.006918
        - 0.399912 * np.cos(B)
        + 0.070257 * np.sin(B)
        - 0.006758 * np.cos(2 * B)
        + 0.000907 * np.sin(2 * B)
        - 0.002697 * np.cos(3 * B)
        + 0.00148 * np.sin(3 * B)
    )

    # Hour angle (rad) - 12h == 0°
    correction = 4 * (psi_std - psi) + Et  # in minutes - From Eq. 1.5.2 (pg.11)
    minute_ap = local_minutes + correction
    hour_ap = local_hours + (local_minutes + correction) / 60.0

    first_condition = hour_ap < 0
    hour_ap[first_condition] = (
        24.0
        + (local_minutes[first_condition] + correction[first_condition]) / 60.0
    )
    minute_ap[first_condition] = 60 + minute_ap[first_condition]

    second_condition = np.logical_and(hour_ap >= 0, minute_ap < 0)

    minute_ap[second_condition] = 60 + minute_ap[second_condition]
    hour_ap[second_condition] = (
        local_hours[second_condition]
        + (local_minutes[second_condition] + correction[second_condition])
        / 60.0
    )

    omega = np.deg2rad((hour_ap - 12.0) * 15.0)

    # Zenith angle (rad) - From Eq. 1.6.5 (pg.16)
    zenith_angle = np.arccos(
        np.cos(phi) * np.cos(delta) * np.cos(omega)
        + np.sin(phi) * np.sin(delta)
    )

    # Extraterrestrial Radiation - From Eq. 1.10.2 (pg. 38)
    Eext = Isc * dr * np.cos(zenith_angle)

    return (Eext, zenith_angle)
