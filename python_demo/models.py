from datetime import datetime, date

from sqlmodel import Column, Field, PickleType, Relationship, SQLModel


def create_db_and_tables(engine):
    """Ensure database and all table definitions match the schema.

    This runs all the data definition commands on the database, creating tables
    and all the properties within them so that the application can work fine.

    """
    SQLModel.metadata.create_all(engine)


class User(SQLModel, table=True):
    """The details of the entity used for logging in.

    We can link the user to different properties uplaoded to the database,
    only providing access to those that they own.

    """

    # This is created automatically by the Database, because the database is
    # responsible for creation until the User is committed to the database the
    # value of the id field is None.
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    hashed_password: str

    # The relationship here is not defining a column within the database, rather
    # a property that the ORM automatically works out for us. the Course table
    # has the user.id column as a foreign key. This will provide a list of all
    # the Courses with the current user.id.
    courses: list["Course"] = Relationship(back_populates="user")


class MLModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    model: PickleType | None = Field(default=None, sa_column=Column(PickleType))

    # To store the machine learning model we need to store it as binary data
    # within the database, rather than one of the structured types. This sets
    # the configuration flag allowing this to occur.
    class Config:
        arbitrary_types_allowed = True


class Course(SQLModel, table=True):
    """Metadata for the collection of points that together make the course.

    This contains the high level data about the course including the user
    uploading it and the name of the course.

    """

    id: int | None = Field(default=None, primary_key=True)
    name: str | None
    user_id: int | None = Field(default=None, foreign_key="user.id")

    points: list["CoursePoints"] = Relationship(
        back_populates="course",
        sa_relationship_kwargs={"order_by": "CoursePoints.time"},
    )
    user: User = Relationship(back_populates="courses")

    # Rather than store this additional data, we can make it available as though it was
    # using the property decorator. This should only be used where the cost of computing
    # the value is low rather than for complex transformations.
    @property
    def date(self) -> date | None:
        """Use the date of the first point as the date of the course."""
        # Handle the case where there are no points in the course. This takes
        # the better to ask forgiveness than permission approach.
        try:
            point = self.points[0]
        except IndexError:
            return None

        return point.time.date()


class CoursePoints(SQLModel, table=True):
    """Point in time recordings of data from a fitness device.

    This pulls together much of the data recorded by the fitness device,
    including the positional information, the time, and physiological metrics.

    """

    id: int | None = Field(default=None, primary_key=True)
    # By  allowing this to be None, we can create the course and all the points
    # at the same time. There is no need to first create the course, then add
    # all the points to it.
    course_id: int | None = Field(default=None, foreign_key="course.id")
    lat: float | None
    lon: float | None
    time: datetime
    power: float | None
    speed: float | None
    heart_rate: int | None
    altitude: int | None

    # Provide a link back to the course
    course: Course | None = Relationship(back_populates="points")
