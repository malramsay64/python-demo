from datetime import datetime
from os import PathLike

import fitdecode
import pandas as pd

from .models import CoursePoints

# Define the type for data within the fit file. It can be any one of the below
# types separated by the vertical bar.
FitData = float | int | str | datetime

colnames_points = [
    "latitude",
    "longitude",
    "lap",
    "timestamp",
    "altitude",
    "temperature",
    "heart_rate",
    "cadence",
    "speed",
    "power",
]

def _get_fit_points( frame: fitdecode.records.FitDataMessage ) -> None | dict[str, FitData]:
    """Extract some data from an FIT frame representing track points."""
    # Step 0: Initialise data output
    data: dict[str, FitData] = {}

    # Step 1: Obtain frame lat and long and convert it from integer to degree 
    # (if frame has lat and long data)
    if not (frame.has_field("position_lat") and frame.has_field("position_long")):
        # Frame does not have any latitude or longitude data. Ignore these
        # frames in order to keep things simple
        return None
    elif (
        frame.get_value("position_lat") is None
        and frame.get_value("position_long") is None
    ):
        # Frame lat or long is None. Ignore frame
        return None
    else:
        data["latitude"] = frame.get_value("position_lat") / ((2**32) / 360)
        data["longitude"] = frame.get_value("position_long") / ((2**32) / 360)

    # Step 2: Extract all other fields
    for field in colnames_points[3:]:
        if frame.has_field(field):
            data[field] = frame.get_value(field)

    return data


# This is taking the definition of the fit_to_dataframes from the fit2gpx
# package and modifying it to suit our use case, primarily the checking of the
# file extension which in the case of the temporary file created when uploading
# isn't used. This removes the check for the extension and we then assign the
# updated method.
#
# This approach is definitely abusing some of the inner workings of python;
# however, is also demonstrates that nearly anything is possible. The main
# reason this is a bad idea is that the underlying class could change,
# and we then have to work out why and fix it.


def fit_to_dataframes(fname: PathLike) -> pd.DataFrame:
    """Takes path to a FIT file returning DataFrames for lap and point data.

    Parameters
    ----------
        fname (str): string representing file path of the FIT file
    Returns:
        dfs (tuple): df containing data about the laps , df containing data
            about the individual points.
    """
    data_points = []
    lap_no = 1
    with fitdecode.FitReader(fname) as fit_file:
        for frame in fit_file:
            if isinstance(frame, fitdecode.records.FitDataMessage):
                # Determine if frame is a data point or a lap:
                if frame.name == "record":
                    single_point_data = _get_fit_points(frame)
                    if single_point_data is not None:
                        single_point_data["lap"] = lap_no  # record lap number
                        data_points.append(single_point_data)

                elif frame.name == "lap":
                    lap_no += 1  # increase lap counter

    # Create DataFrames from the data we have collected. (If any information
    # is missing from a lap or track point, it will show up as a "NaN" in the
    # DataFrame.)

    df_points = pd.DataFrame(data_points, columns=colnames_points)

    return df_points


def decode_fit(file) -> list[CoursePoints]:
    """Decode the values within a file to Points within a course."""
    df_point = fit_to_dataframes(fname=file)

    return [
        CoursePoints(
            lat=row.latitude,
            lon=row.longitude,
            time=row.timestamp,
            heart_rate=row.heart_rate,
            power=row.power,
            altitude=row.altitude,
            speed=row.speed,
        )
        for _, row in df_point.iterrows()
    ]
