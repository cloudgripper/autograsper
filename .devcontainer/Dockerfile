FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app


RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
