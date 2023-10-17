FROM python:3.10-slim

ARG http_proxy=http://internet.ford.com:83
ARG https_proxy=http://internet.ford.com:83

WORKDIR /app
COPY . /app
COPY requirements.txt ./requirements.txt

RUN pip3 install -r requirements.txt 

EXPOSE 8088

CMD exec gunicorn --bind :8080 --workers 1 --threads 8 --timeout 0 main:app