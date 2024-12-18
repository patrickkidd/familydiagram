FROM python:3.11-slim

ARG TWINE_REPOSITORY_URL
ARG TWINE_USERNAME
ARG TWINE_PASSWORD
ENV PYTHONUNBUFFERED=1

# System

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    libssl-dev \
    qtbase5-dev \
    qtchooser \
    qt5-qmake \
    qtbase5-dev-tools \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
    
RUN pip install --upgrade pip
RUN pip install pipenv

# App

WORKDIR /app

COPY Pipfile .
RUN rm -rf .venv
RUN mkdir .venv
RUN pipenv install --dev --verbose
RUN pipenv run which sip-install


# RUN git clone --verbose https://github.com/patrickkidd/familydiagram.git .
COPY pkdiagram pkdiagram

RUN cd _pkdiagram && \
    pipenv run sip-install
RUN cd _pkdiagram && \
    moc -o build/_pkdiagram/moc_unsafearea.cpp unsafearea.h
RUN cd _pkdiagram && \
    moc -o build/_pkdiagram/moc__pkdiagram.cpp _pkdiagram.h 


COPY bin bin
RUN pipenv run python bin/update_build_info.py

COPY tests tests
COPY python_init.py python_init.py

CMD ["pipenv", "run", "pytest", "-svv", "./tests"]
