import os
import random
import subprocess
import time
from dataclasses import dataclass
from threading import Thread
from typing import Dict
from uuid import uuid4

import requests
from flask import Flask, Response, request
from flask_cors import CORS, cross_origin
from starknet_py.net.gateway_client import GatewayClient
from starknet_py.net.networks import TESTNET

from cairo_sandbox import get_shared_secret

HTTP_PORT = os.getenv("HTTP_PORT", "5050")

app = Flask(__name__)
CORS(app)


@dataclass
class NodeInfo:
    port: str
    seed: str
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
    port = str(random.randrange(30000, 60000))

    seed = str(random.getrandbits(32))
    uuid = str(uuid4())

    proc = subprocess.Popen(
        args=[
            "starknet-devnet",
            "--port",
            port,
            "--accounts",
            "2",  # first account is the deployer, second account is for the user
            "--seed",
            seed,
        ],
    )

    client = GatewayClient(f"http://127.0.0.1:{port}", TESTNET)
    while True:
        if proc.poll() is not None:
            return None

        try:
            client.get_block_sync(block_number=0)
            break
        except:
            pass
        time.sleep(0.1)

    node_info = NodeInfo(port=port, seed=seed, proc=proc, uuid=uuid, team=team_id)
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
        "seed": node_info.seed,
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


ALLOWED_NAMESPACES = ["starknet"]


@app.route("/<path:path>", methods=["GET"])
@cross_origin()
def proxy_get(path):
    uuid = request.authorization.username
    if uuid not in instances_by_uuid:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32602,
                "message": "invalid uuid specified",
            },
        }

    instance = instances_by_uuid[uuid]
    url = f"http://127.0.0.1:{instance.port}/{path}?{request.query_string.decode('utf-8')}"
    # print("proxying request to", url)
    resp = requests.request(
        method=request.method,
        url=url,
        headers={key: value for (key, value) in request.headers if key != "Host"},
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False,
    )
    response = Response(resp.content, resp.status_code, resp.raw.headers.items())
    # print("proxied response is", resp.content)
    return response


@app.route("/<path:path>", methods=["POST"])
@cross_origin()
def proxy(path):
    uuid = request.authorization.username

    body = request.get_json()
    if not body:
        return "invalid content type, only application/json is supported"

    # print("body is", body)

    if uuid not in instances_by_uuid:
        return {
            "jsonrpc": "2.0",
            "id": body["id"],
            "error": {
                "code": -32602,
                "message": "invalid uuid specified",
            },
        }

    instance = instances_by_uuid[uuid]
    resp = requests.post(f"http://127.0.0.1:{instance.port}/{path}", json=body)
    response = Response(resp.content, resp.status_code, resp.raw.headers.items())
    # print("response is", resp.content)
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(HTTP_PORT))
