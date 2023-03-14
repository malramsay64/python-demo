import geopy.distance
import pandas as pd
from sklearn.linear_model import LinearRegression
from sqlmodel import SQLModel


def sqmodel_to_df(objs: list[SQLModel]) -> pd.DataFrame:
    """Convert a SQLModel objects into a pandas DataFrame."""
    records = [i.dict() for i in objs]
    return pd.DataFrame.from_records(records)


def calculate_gradient(
    # Typing support within the python ecosystem is still a little incomplete,
    # in this case with the handling of pandas Series hence the quotation marks
    lat: "pd.Series[float]", 
    lon: "pd.Series[float]", 
    altitude: "pd.Series[float]"
) -> "pd.Series[float]":
    """Use the position and altitude to find the gradient at each point.

    This finds the distance between the previous point and the current one to
    calculate the distance and the difference in altitude between the previous
    point and the current one.

    """
    points = pd.Series([geopy.Point(lat, lon) for lat, lon in zip(lat, lon)])
    run = pd.Series(
        [
            geopy.distance.distance(point_prev, point).meters
            for point_prev, point in zip(points.shift(-1), points)
        ]
    )
    # The altitude data is very noisy, so by performing an exponentially weighted
    # mean we are able to smooth the data and remove the noise.
    altitude = altitude.ewm(span=11).mean()
    rise = altitude.shift(-1) - altitude

    # Calculate the gradient and convert to percentage
    return (rise / run) * 100


def generate_model(objs: list[SQLModel]):
    df = (
        sqmodel_to_df(objs)
        .assign(
            speed_kmh=lambda x: x["speed"] * 3.6,
            gradient=lambda x: calculate_gradient(x["lat"], x["lon"], x["altitude"])
        )
        # Having NA values within the Machine Learning model will give rise to 
        # errors so we remove them here.
        .dropna(subset=["gradient", "speed", "power"])
    )
    model = LinearRegression()
    X = df[["speed_kmh", "gradient"]]
    y = df["power"]
    model.fit(X, y)
    return model
