# Using official python runtime base image
FROM python:3.7-alpine

# Set the application directory
WORKDIR /telegram_bot

# Install our requirements.txt
ADD requirements.txt /telegram_bot/requirements.txt
#LIBRARY_PATH=/lib:/usr/lib \
 #    LIBRARY_PATH=/lib:/usr/lib \
RUN apk add --no-cache \
        # Pillow dependencies
        jpeg-dev \
        zlib-dev \
    && apk add --no-cache --virtual .build-deps \
        gcc \
        # criptografy -> python-telegram-bot dependencies
        musl-dev \
        libffi-dev \
        openssl-dev \
    && pip install -r requirements.txt \
    && apk del .build-deps

# Copy our code from the current folder to /app inside the container
ADD . /telegram_bot

# Define our command to be run when launching the container
ENV ROUTE_TIME_BOT_TOKEN=${ROUTE_TIME_BOT_TOKEN}
ENV PYTHONPATH=/:$PYTHONPATH
CMD ["python", "main.py"]
