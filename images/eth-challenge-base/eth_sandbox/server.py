import os
import random
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from threading import Lock, Thread
from typing import Any, Dict, Tuple
from uuid import uuid4

import requests
from eth_account.hdaccount import generate_mnemonic
from flask import Flask, Response, redirect, request
from flask_cors import CORS, cross_origin
from web3 import Web3

from eth_sandbox import *

app = Flask(__name__)
CORS(app)

HTTP_PORT = os.getenv("HTTP_PORT", "8545")
ETH_RPC_URL = os.getenv("ETH_RPC_URL")


@dataclass
class NodeInfo:
    port: str
    mnemonic: str
    proc: subprocess.Popen
    uuid: str
    team: str


instances_by_uuid: Dict[str, NodeInfo] = {}
instances_by_team: Dict[str, NodeInfo] = {}


def really_kill_node(node_info: NodeInfo):
    print(f"killing node {node_info.team} {node_info.uuid}")

    del instances_by_uuid[node_info.uuid]
    del instances_by_team[node_info.team]

    node_info.proc.kill()


def kill_node(node_info: NodeInfo):
    time.sleep(60 * 30)

    if node_info.uuid not in instances_by_uuid:
        return

    really_kill_node(node_info)


def launch_node(team_id: str) -> NodeInfo:
    port = random.randrange(30000, 60000)
    mnemonic = generate_mnemonic(12, "english")
    uuid = str(uuid4())

    proc = subprocess.Popen(
        args=[
            "/root/.foundry/bin/anvil",
            "--accounts",
            "2",  # first account is the deployer, second account is for the user
            "--balance",
            "5000",
            "--mnemonic",
            mnemonic,
            "--port",
            str(port),
            "--fork-url",
            ETH_RPC_URL,
            "--block-base-fee-per-gas",
            "0",
        ],
    )

    web3 = Web3(Web3.HTTPProvider(f"http://127.0.0.1:{port}"))
    while True:
        if proc.poll() is not None:
            return None
        if web3.isConnected():
            break
        time.sleep(0.1)

    node_info = NodeInfo(
        port=port, mnemonic=mnemonic, proc=proc, uuid=uuid, team=team_id
    )
    instances_by_uuid[uuid] = node_info
    instances_by_team[team_id] = node_info

    reaper = Thread(target=kill_node, args=(node_info,))
    reaper.start()
    return node_info


def is_request_authenticated(request):
    token = request.headers.get("Authorization")

    return token == f"Bearer {get_shared_secret()}"


@app.route("/")
def index():
    return "sandbox is running!"


@app.route("/new", methods=["POST"])
@cross_origin()
def create():
    if not is_request_authenticated(request):
        return {
            "ok": False,
            "error": "nice try",
        }

    body = request.get_json()

    team_id = body["team_id"]

    if team_id in instances_by_team:
        print(f"refusing to run a new chain for team {team_id}")
        return {
            "ok": False,
            "error": "already_running",
            "message": "An instance is already running!",
        }

    node_info = launch_node(team_id)
    if node_info is None:
        print(f"failed to launch node for team {team_id}")
        return {
            "ok": False,
            "error": "error_starting_chain",
            "message": "An error occurred while starting the chain",
        }

    return {
        "ok": True,
        "uuid": node_info.uuid,
        "mnemonic": node_info.mnemonic,
    }


@app.route("/kill", methods=["POST"])
@cross_origin()
def kill():
    if not is_request_authenticated(request):
        return {
            "ok": False,
            "error": "nice try",
        }

    body = request.get_json()

    team_id = body["team_id"]

    if team_id not in instances_by_team:
        print(f"no instance to kill for team {team_id}")
        return {
            "ok": False,
            "error": "not_running",
            "message": "No instance is running!",
        }

    really_kill_node(instances_by_team[team_id])

    return {
        "ok": True,
        "message": "Instance killed",
    }


ALLOWED_NAMESPACES = ["web3", "eth", "net"]


@app.route("/<string:uuid>", methods=["POST"])
@cross_origin()
def proxy(uuid):
    body = request.get_json()
    if not body:
        return "invalid content type, only application/json is supported"

    if "id" not in body:
        return ""

    if uuid not in instances_by_uuid:
        return {
            "jsonrpc": "2.0",
            "id": body["id"],
            "error": {
                "code": -32602,
                "message": "invalid uuid specified",
            },
        }

    if "method" not in body or not isinstance(body["method"], str):
        return {
            "jsonrpc": "2.0",
            "id": body["id"],
            "error": {
                "code": -32600,
                "message": "invalid request",
            },
        }

    ok = (
        any(body["method"].startswith(namespace) for namespace in ALLOWED_NAMESPACES)
        and body["method"] != "eth_sendUnsignedTransaction"
    )
    if not ok and not is_request_authenticated(request):
        return {
            "jsonrpc": "2.0",
            "id": body["id"],
            "error": {
                "code": -32600,
                "message": "invalid request",
            },
        }

    instance = instances_by_uuid[uuid]
    resp = requests.post(f"http://127.0.0.1:{instance.port}", json=body)
    response = Response(resp.content, resp.status_code, resp.raw.headers.items())
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=HTTP_PORT)
