from datetime import datetime
from fastapi import FastAPI
from fit2gpx import Converter
from sqlmodel import Field, Relationship, SQLModel, Session, create_engine

_, df_points = Converter().fit_to_dataframes("tests/activity.fit")

df_points.head()

sqlite_url = "sqlite:///:memory:"
engine = create_engine(sqlite_url, echo=True)

session = Session(engine)


class Course(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str | None

    points: list["CoursePoint"] = Relationship()


class CoursePoint(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    course_id: int | None = Field(default=None, foreign_key="course.id")
    lat: float
    lon: float
    time: datetime
    power: float | None
    speed: float | None
    heart_rate: int | None
    altitude: int | None


SQLModel.metadata.create_all(engine)

points = [
    CoursePoint(
        lat=row.latitude,
        lon=row.longitude,
        time=row.timestamp,
        power=row.power,
        altitude=row.altitude,
        heart_rate=row.heart_rate,
        speed=row.speed,
    )
    for _, row in df_points.head(10).iterrows()
]
print(points)

course = Course(name="Test", points=points)

session.add(course)
session.commit()
print(course.id)

app = FastAPI()

@app.get("/course/{course_id}")
def read_course(course_id: int) -> Course:
    return session.get(Course, course_id)