FROM python:3.10-slim

ARG TWINE_REPOSITORY_URL
ARG TWINE_USERNAME
ARG TWINE_PASSWORD
ENV TWINE_REPOSITORY_URL=${TWINE_REPOSITORY_URL}
ENV TWINE_USERNAME=${TWINE_USERNAME}
ENV TWINE_PASSWORD=${TWINE_PASSWORD}
ENV PYTHONUNBUFFERED=1

# System

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    qtbase5-dev \
    qtchooser \
    qt5-qmake \
    qtbase5-dev-tools \
    cmake \
    && rm -rf /var/lib/apt/lists/*
    
RUN pip install --upgrade pip
RUN pip install pipenv

# App

WORKDIR /app

COPY . .

# RUN git clone --verbose https://github.com/patrickkidd/familydiagram.git .

RUN rm -rf .venv
RUN mkdir .venv
RUN pipenv install --dev --skip-lock --verbose
RUN pipenv run which sip-install

RUN cmake .
RUN make
RUN pipenv run python bin/update_build_info.py

CMD ["pipenv", "run", "pytest", "-svv", "./tests"]
