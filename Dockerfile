FROM python:3.7-slim-buster

RUN apt update
RUN apt -y install ruby ruby-dev
RUN gem install gazer

COPY . /app
WORKDIR /app
RUN pip install .
WORKDIR /
ENTRYPOINT ["ldeploy"]
