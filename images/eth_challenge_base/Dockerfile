FROM gcr.io/paradigmxyz/ctf/base:latest

ENV HTTP_PORT=8545

RUN true \
    && curl -L https://foundry.paradigm.xyz | bash \
    && bash -c "source /root/.bashrc && foundryup" \
    && echo "export PATH='$PATH:$HOME/.foundry/bin'" > ~/.profile \
    && true

COPY requirements.txt /root

RUN python3 -m pip install -r /root/requirements.txt 

COPY 98-start-gunicorn /startup

COPY eth_sandbox /usr/lib/python/eth_sandbox

ENV PYTHONPATH /usr/lib/python
