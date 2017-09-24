FROM python:2-alpine

RUN apk add --no-cache python-dev
RUN apk add --no-cache openssl-dev
RUN apk add --no-cache libffi-dev
RUN apk add --no-cache build-base
RUN apk add --no-cache py-virtualenv
RUN apk add --no-cache linux-headers

RUN virtualenv /app/env

COPY requirements.txt /src/requirements.txt
RUN /app/env/bin/pip install -r /src/requirements.txt

COPY . /src

RUN /app/env/bin/pip install /src

FROM python:2-alpine

RUN apk add --no-cache py-virtualenv

COPY --from=0 /app/env /app/env

VOLUME /data

ENTRYPOINT ["/app/env/bin/txflashair-sync"]
CMD ["--device-root", "/DCIM", "--local-root", "/data", "--include", "IMG_*.JPG"]
