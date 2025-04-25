
FROM python:3.11.4-slim-buster


ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt /app/

RUN apt-get update && apt-get install -y netcat

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

COPY . /app/