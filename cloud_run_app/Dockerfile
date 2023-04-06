FROM python:3.10-slim

ARG http_proxy=http://internet.ford.com:83
ARG https_proxy=http://internet.ford.com:83

WORKDIR /app
COPY . /app
COPY requirements.txt ./requirements.txt

RUN pip3 install -r requirements.txt 

EXPOSE 8080

ENTRYPOINT [ "python3", "main.py"] 
