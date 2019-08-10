## Using official python runtime base image
FROM python:3.7-alpine

# Set the application directory
WORKDIR /app

# Install our requirements.txt
ADD requirements.txt /app/requirements.txt
RUN set -e; \
	apk add --no-cache --virtual .build-deps \
		gcc \
		libc-dev \
		linux-headers \
	; \
	pip install -r requirements.txt; \
	apk del .build-deps;

# Copy our code from the current folder to /app inside the container
ADD . /app

# Expose the port uWSGI will listen on
EXPOSE 5000

# Finally, we run uWSGI with the ini file we
# created earlier
CMD [ "uwsgi", "--ini", "./conf/uwsgi.ini" ]