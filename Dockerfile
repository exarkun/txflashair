FROM python:2-alpine

COPY . /src
RUN apk add --no-cache python-dev
RUN apk add --no-cache openssl-dev
RUN apk add --no-cache libffi-dev
RUN apk add --no-cache build-base

RUN pip install /src

VOLUME /data

ENTRYPOINT ["txflashair-sync"]
CMD ["--device-root", "/DCIM", "--local-root", "/data", "--include", "IMG_*.JPG"]
