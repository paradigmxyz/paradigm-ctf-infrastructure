FROM gcr.io/paradigmxyz/ctf/base:latest

ENV HTTP_PORT=5050

COPY requirements.txt /root

RUN true \
    && python3 -m pip install -r /root/requirements.txt \
    && apt update \
    && apt install -y libgmp3-dev \
    && rm -rf /var/cache/apt/archives \
    && true

COPY 98-start-gunicorn /startup

COPY cairo_sandbox /usr/lib/python/cairo_sandbox

ENV PYTHONPATH /usr/lib/python
