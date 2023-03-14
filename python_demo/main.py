import os
from datetime import timedelta

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException
from sqlmodel import Session, create_engine, select

from .authentication import get_password_hash, verify_password
from .course import decode_fit
from .machine_learning import generate_model
from .models import Course, CoursePoints, MLModel, User, create_db_and_tables

# Configuration for the templating.
templates = Jinja2Templates(directory="templates")

# Configuration for the authentication.
# This is particularly important because we don't want to include the SECRET_KEY
# within the git repository. This allows us to set the value within a `.env`
# configuration file while also having the ability to set this through
# environment variables.
load_dotenv()

# This is where we load the value of the environment variable for the secret
# key. This could have either been in our .env file and automatically loaded
# above, or in production defined as an environment variable.
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
manager = LoginManager(SECRET_KEY, token_url="/auth", use_cookie=True)


# Configuration of the database
# Here we are using sqlite as it is included within python and there are no
# separate services to start and manage.
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# This stops the check that the SQL model object is created on the same thread
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


def get_session():
    with Session(engine) as session:
        yield session


# Configure and setup the FastAPI application
app = FastAPI()


# the python-multipart package is required to use the OAuth2PasswordRequestForm
@app.post("/auth")
def login(
    request: Request,
    data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_session),
):
    # we are using the same function to retrieve the user
    user = load_user(data.username, db)
    if not user:
        raise InvalidCredentialsException
    elif not verify_password(data.password, user.hashed_password):
        raise InvalidCredentialsException

    context = {
        "request": request,
        "success_msg": "Login Successful!",
        "path_route": "/home",
        "path_msg": "Click here to go to your Home Page!",
    }
    response = templates.TemplateResponse("success.html", context)
    # When the user reconnects, this value is used to determine who the user is
    # and that they have logged in. It is provided in the form of a cookie that
    # is attached to every following request. The expiry time of the cookie can
    # be managed although the time should be kept relatively short.
    access_token = manager.create_access_token(
        data={"sub": data.username}, expires=timedelta(minutes=60)
    )
    # We have to tell the login manager to set the cookie manually.
    manager.set_cookie(response, access_token)
    return response


@manager.user_loader(session=next(get_session()))
def load_user(username: str, session):
    """Ensure the user is loaded to provide access to properties.

    Note:
        When working with the user object and other sessions, that is when
        trying to update the user within a function call, the session used is
        different to the session that is used here causing problems. The way
        around this is to use the user_id property rather than trying to update
        the user directly.

    """
    return session.exec(select(User).where(User.username == username)).one()


# When the FastAPI application starts, is will run the "startup" events. For
# this application we need to ensure the database has been created and the
# schema is up to date.
@app.on_event("startup")
def on_startup():
    create_db_and_tables(engine)


@app.get("/")
def index(request: Request):
    context = {
        "request": request,
    }
    return templates.TemplateResponse("index.html", context)


@app.get("/signup")
def signup(request: Request):
    context = {
        "request": request,
    }
    return templates.TemplateResponse("sign_up.html", context)


@app.post("/user")
def new_user(
    request: Request,
    username=Form(),
    password=Form(),
    session: Session = Depends(get_session),
):
    if session.exec(select(User).where(User.username == username)).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User Exists")

    # Create the new user and store within the database. This doesn't persist
    # until we call the session.commit() method.
    session.add(
        User(
            username=username,
            hashed_password=get_password_hash(password),
        )
    )
    session.commit()

    context = {
        "request": request,
        "success_msg": "Registration Successful!",
        "path_route": "/",
        "path_msg": "Click here to login!",
    }
    return templates.TemplateResponse("success.html", context)


@app.post("/course")
def post_course(
    # Normally arguments without a default value have to come before those that don't,
    # this is to properly handle positional and keyword arguments. By putting the *,
    # we are forcing all these arguments to be specified by keyword, that is 
    # post_course(file="filename", name="test", ...). This then means we can put
    # them in any order.
    *,
    file: UploadFile,
    name: str | None = None,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(manager),
):
    """Upload and store a course for the currently logged in user.

    This allows us to upload a file and persist the data within the database.
    """
    # The UploadFile class handles creating a temporary file for us, so we can use
    # the file property to pass this temporary file to any other function.
    points = decode_fit(file.file)
    if name is not None:
        name = name
    else:
        name = file.filename
    course = Course(user_id=user.id, name=name, points=points)
    session.add(course)
    session.commit()
    # Ensure all the database created values like ids and relationships are
    # refreshed and up to date.
    session.refresh(course)

    # This context is used by the template to fill in values
    context = {
        "request": request,
        "success_msg": "Course upload Successful!",
        "path_route": f"/course/{course.id}",
        "path_msg": "Click here to view the course!",
    }
    return templates.TemplateResponse("success.html", context)


@app.get("/home")
def read_my_home(request: Request, current_user: User = Depends(manager)):
    context = {
        "username": current_user.username,
        "request": request,
        "courses": current_user.courses,
    }
    return templates.TemplateResponse("home.html", context)


@app.get("/course/{course_id}")
def read_courses(
    course_id: int,
    request: Request,
    current_user: User = Depends(manager),
    session: Session = Depends(get_session),
):
    course = session.get(Course, course_id)
    if course.user != current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Course does not belong to current user.",
        )

    context = {
        "request": request,
        "course": course,
    }
    return templates.TemplateResponse("course.html", context)


@app.get("/course/{course_id}/points")
def read_course_points(
    course_id: int,
    current_user: User = Depends(manager),
    session: Session = Depends(get_session),
) -> list[CoursePoints]:
    course = session.get(Course, course_id)
    if course.user != current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Course does not belong to current user.",
        )

    return course.points


@app.get("/predict")
def get_predict(
    request: Request,
    current_user: User = Depends(manager),
    session: Session = Depends(get_session),
):
    context = {
        "request": request,
    }
    return templates.TemplateResponse("predict.html", context)


@app.post("/predict")
def get_predict_post(
    *,
    speed: float = Form(),
    gradient: float = Form(),
    request: Request,
    current_user: User = Depends(manager),
    session: Session = Depends(get_session),
) -> float:
    ml_model = session.exec(
        select(MLModel).where(MLModel.user_id == current_user.id)
    ).one_or_none()

    if ml_model is None or ml_model.model is None:
        query = (
            select(CoursePoints)
            .join(Course)
            .where(Course.user_id == current_user.id)
            .order_by(CoursePoints.course_id, CoursePoints.time)
        )
        model = generate_model(session.exec(query).fetchall())
        if ml_model is None:
            ml_model = MLModel(user_id=current_user.id, model=model)
        else:
            ml_model.model = model
        session.add(ml_model)
        session.commit()
        session.refresh(ml_model)

    # Calculate the predicted power output
    power = ml_model.model.predict([[speed, gradient]])[0]

    context = {
        "request": request,
        "power": power,
        "speed": speed,
        "gradient": gradient,
    }
    return templates.TemplateResponse("prediction.html", context)
