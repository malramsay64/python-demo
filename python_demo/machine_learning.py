from .models import MLModel, User, CoursePoints
import pandas as pd
from sklearn.linear_model import LinearRegression
from sqlmodel import Session, select
import geopy.distance
from sqlmodel import SQLModel


def sqmodel_to_df(objs: list[SQLModel]) -> pd.DataFrame:
    """Convert a SQLModel objects into a pandas DataFrame."""
    records = [i.dict() for i in objs]
    return pd.DataFrame.from_records(records)


def generate_model(objs: list[SQLModel]):
    df = (
        sqmodel_to_df(objs)
        .assign(
                speed_kmh=lambda x: x["speed"] * 3.6,
                point=lambda x: x.apply(lambda row: geopy.Point(row["lat"], row["lon"]), axis=1),
        )
        # .groupby("course_id")
        .assign(
                point_prev= lambda x: x["point"].shift(-1),
                altitude_prev= lambda x: x["altitude"].shift(-1),
        )
        .dropna(subset=["point_prev", "power"])
        .assign(
                distance= lambda x: x.apply(
                    lambda row: geopy.distance.distance(row["point_prev"], row["point"]).meters, axis=1
                ),
                altitude_gain= lambda x: x["altitude_prev"] - x["altitude"],
        )
        .assign(gradient= lambda x: x["altitude_gain"] / x["distance"] * 100)
    )
    model = LinearRegression()
    X = df[["speed_kmh", "gradient"]]
    y = df["power"]
    model.fit(X, y)
    return model
