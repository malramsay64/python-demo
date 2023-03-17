# python-demo

This is a project to demonstrate the range of use cases for python,
from data analysis, and machine learning, managing a database,
to running a web application.

## Installation Prerequisites

This project requires python 3.9 or above and is tested
to install on linux, macos, and windows.

The project uses [poetry] to manage 
the installation of packages and the environment.
Installation of poetry is required before running the project
which can be done by running the below command in the shell.

```shell
python -m pip install poetry
```

Should there be issues when running this,
it is likely that `pip` is trying to install poetry for all users.
This behaviour can be overwritten by setting the `--user` flag like so

```shell
python -m pip install --user poetry
```

with poetry installed and a compatible version of python
we can move onto the installation of the dependencies.

## Installing Dependencies

With poetry managing the dependencies,
the process to manage the installation is running the command

```shell
poetry install
```

This will check that you are using a compatible version of python
and install the exact versions of all the required dependencies.

It is also possible to not include any of the development dependencies
adding only those needed for running the application using the command

```shell
poetry install --without dev
```

## Running the Application

With all the dependencies installed
it is now possible to run the application.
This is a [FastAPI] web application
so we can start it with the command

```shell
poetry run uvicorn python_demo.main:app
```

while developing it can be useful
to have the application automatically reload as changes are made.
This can be enabled with the `--reload` flag like so

```shell
poetry run uvicorn python_demo.main:app --reload
```


[poetry]: https://python-poetry.org/
[FastAPI]: https://fastapi.tiangolo.com/