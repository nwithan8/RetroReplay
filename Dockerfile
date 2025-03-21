FROM python:3.10-alpine AS base

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN python -m pip install -r requirements.txt

FROM base AS final
WORKDIR /app
COPY . .

ENTRYPOINT ["python", "main.py"]