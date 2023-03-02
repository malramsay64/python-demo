from fit2gpx import Converter
from .models import CoursePoints
import fitdecode
from os import PathLike
import pandas as pd
from typing import Tuple


def fit_to_dataframes(self, fname: PathLike) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Takes the path to a FIT file and returns two Pandas DataFrames for lap data and point data
    Parameters:
        fname (str): string representing file path of the FIT file
    Returns:
        dfs (tuple): df containing data about the laps , df containing data about the individual points.
    """
    data_points = []
    data_laps = []
    lap_no = 1
    with fitdecode.FitReader(fname) as fit_file:
        for frame in fit_file:
            if isinstance(frame, fitdecode.records.FitDataMessage):
                # Determine if frame is a data point or a lap:
                if frame.name == "record":
                    single_point_data = self._get_fit_points(frame)
                    if single_point_data is not None:
                        single_point_data["lap"] = lap_no  # record lap number
                        data_points.append(single_point_data)

                elif frame.name == "lap":
                    single_lap_data = self._get_fit_laps(frame)
                    single_lap_data["number"] = lap_no
                    data_laps.append(single_lap_data)
                    lap_no += 1  # increase lap counter

    # Create DataFrames from the data we have collected.
    # (If any information is missing from a lap or track point, it will show up as a "NaN" in the DataFrame.)

    df_laps = pd.DataFrame(data_laps, columns=self._colnames_laps)
    df_laps.set_index("number", inplace=True)
    df_points = pd.DataFrame(data_points, columns=self._colnames_points)

    return df_laps, df_points


Converter.fit_to_dataframes = fit_to_dataframes


def decode_fit(file):
    conv = Converter()
    _, df_point = conv.fit_to_dataframes(fname=file)

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
