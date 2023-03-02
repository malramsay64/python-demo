from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, Session, select, PickleType, Column
from pydantic import BaseModel
from sklearn.linear_model import LinearRegression


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class UserNew(BaseModel):
    username: str
    password: str


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    hashed_password: str

    courses: list["Course"] = Relationship(back_populates="user")


class MLModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    model: PickleType | None = Field(default=None, sa_column=Column(PickleType))

    class Config:
        arbitrary_types_allowed = True


class Course(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str | None
    user_id: int | None = Field(default=None, foreign_key="user.id")

    points: list["CoursePoints"] = Relationship(
        back_populates="course",
        sa_relationship_kwargs={"order_by": "CoursePoints.time"},
    )
    user: User = Relationship(back_populates="courses")

    @property
    def date(self) -> datetime | None:
        """Use the date of the first point as the date of the course."""
        # Handle the case where there are no points in the course. This takes
        # the better to ask forgiveness than permission approach.
        try:
            point = self.points[0]
        except IndexError:
            return None

        return point.time.date()


class CoursePoints(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    course_id: int | None = Field(default=None, foreign_key="course.id")
    lat: float | None
    lon: float | None
    time: datetime
    power: float | None
    speed: float | None
    heart_rate: int | None
    altitude: int | None

    course: Course | None = Relationship(back_populates="points")
