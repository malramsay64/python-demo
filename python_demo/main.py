from .models import Token, User, Course, MLModel
from .course import decode_fit
from passlib.hash import argon2
from jose import jwt, JWTError
from .models import User, TokenData, UserNew, CoursePoints
from .machine_learning import generate_model
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    status,
    Form,
    Response,
    Request,
    UploadFile,
)
import pandas as pd
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import SQLModel, create_engine, Session, select
from fastapi_login import LoginManager
from fastapi_login.exceptions import InvalidCredentialsException

from dotenv import dotenv_values

templates = Jinja2Templates(directory="templates")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return argon2.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return argon2.hash(password)


config = dotenv_values(".env")
SECRET_KEY = config["SECRET_KEY"]
ALGORITHM = "HS256"

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# This stops the check that the SQL model object is created on the same thread
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)

manager = LoginManager(SECRET_KEY, token_url="/auth", use_cookie=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


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
        raise InvalidCredentialsException  # you can also use your own HTTPException
    elif not verify_password(data.password, user.hashed_password):
        raise InvalidCredentialsException

    context = {
        "request": request,
        "success_msg": "Registration Successful!",
        "path_route": "/home",
        "path_msg": "Click here to go to your Home Page!",
    }
    response = templates.TemplateResponse("success.html", context)
    access_token = manager.create_access_token(data={"sub": data.username})
    manager.set_cookie(response, access_token)
    return response


@manager.user_loader(session=next(get_session()))
def load_user(username: str, session):
    return session.exec(select(User).where(User.username == username)).one()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    context = {
        "request": request,
    }
    return templates.TemplateResponse("index.html", context)


@app.get("/signup", response_class=HTMLResponse)
def signup(request: Request):
    context = {
        "request": request,
    }
    return templates.TemplateResponse("sign_up.html", context)


@app.post("/user", response_class=HTMLResponse)
def new_user(
    request: Request,
    username=Form(),
    password=Form(),
    session: Session = Depends(get_session),
):
    if session.exec(select(User).where(User.username == username)).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User Exists")

    session.add(
        User(
            username=username,
            hashed_password=get_password_hash(password),
        )
    )

    session.commit()
    # return RedirectResponse("/")
    # TODO verify success and handle errors
    response = templates.TemplateResponse(
        "success.html",
        {
            "request": request,
            "success_msg": "Registration Successful!",
            "path_route": "/",
            "path_msg": "Click here to login!",
        },
    )
    return response


@app.post("/course")
def post_course(
    *,
    file: UploadFile,
    name: str | None = None,
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(manager),
):
    points = decode_fit(file.file)
    if name is not None:
        name = name
    else:
        name = file.filename
    course = Course(user_id=user.id, name=name, points=points)
    session.add(course)
    session.commit()
    session.refresh(course)

    context = {
        "request": request,
        "success_msg": "Registration Successful!",
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

    response = templates.TemplateResponse(
        "course.html",
        {
            "request": request,
            "course": course,
        },
    )
    return response


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
    response = templates.TemplateResponse(
        "predict.html",
        {
            "request": request,
        },
    )
    return response


@app.post("/predict")
def get_predict(
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

    return ml_model.model.predict([[speed, gradient]])[0]
