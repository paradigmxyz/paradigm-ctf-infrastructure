import asyncio
import json
import os
import random
import string
from dataclasses import dataclass
from typing import Callable, List

import requests
from starknet_py.contract import Contract
from starknet_py.net import AccountClient, KeyPair
from starknet_py.net.gateway_client import GatewayClient
from starknet_py.net.models.chains import StarknetChainId
from starknet_py.net.networks import TESTNET
from starkware.crypto.signature.signature import private_to_stark_key
from starkware.starknet.core.os.contract_address.contract_address import \
    calculate_contract_address_from_hash

from cairo_sandbox import get_shared_secret

HTTP_PORT = os.getenv("HTTP_PORT", "5050")
PUBLIC_IP = os.getenv("PUBLIC_IP", "127.0.0.1")

CHALLENGE_ID = os.getenv("CHALLENGE_ID", "challenge")
ENV = os.getenv("ENV", "dev")
FLAG = os.getenv("FLAG", "PCTF{placeholder}")


@dataclass
class Ticket:
    challenge_id: string
    team_id: string


def check_ticket(ticket: str) -> Ticket:
    if ENV == "dev":
        return Ticket(challenge_id=CHALLENGE_ID, team_id="team")

    ticket_info = requests.get(
        f"https://us-central1-paradigm-ctf-2022.cloudfunctions.net/checkTicket?ticket={ticket}"
    ).json()
    if ticket_info["status"] != "VALID":
        return None

    return Ticket(
        challenge_id=ticket_info["challengeId"], team_id=ticket_info["teamId"]
    )


@dataclass
class Action:
    name: str
    handler: Callable[[], int]


def new_launch_instance_action(
    do_deploy: Callable[[GatewayClient, int], str],
):
    async def action() -> int:
        ticket = check_ticket(input("ticket please: "))
        if not ticket:
            print("invalid ticket!")
            return 1

        if ticket.challenge_id != CHALLENGE_ID:
            print("invalid ticket!")
            return 1

        data = requests.post(
            f"http://127.0.0.1:{HTTP_PORT}/new",
            headers={
                "Authorization": f"Bearer {get_shared_secret()}",
                "Content-Type": "application/json",
            },
            data=json.dumps(
                {
                    "team_id": ticket.team_id,
                }
            ),
        ).json()

        if data["ok"] == False:
            print(data["message"])
            return 1

        uuid = data["uuid"]
        seed = data["seed"]

        # https://github.com/Shard-Labs/starknet-devnet/blob/660c0064b36a0eb4376ae7da38f2b8e8cb82f55e/starknet_devnet/accounts.py
        random_generator = random.Random()
        random_generator.seed(int(seed))

        deployer_private_key = random_generator.getrandbits(128)
        deployer_public_key = private_to_stark_key(deployer_private_key)

        player_private_key = random_generator.getrandbits(128)
        player_public_key = private_to_stark_key(player_private_key)
        player_address = calculate_contract_address_from_hash(
            salt=20,
            class_hash=1803505466663265559571280894381905521939782500874858933595227108099796801620,
            constructor_calldata=[player_public_key],
            deployer_address=0,
        )

        client = GatewayClient(f"http://{uuid}@127.0.0.1:{HTTP_PORT}", TESTNET)
        # https://github.com/Shard-Labs/starknet-devnet/blob/a5c53a52dcf453603814deedb5091ab8c231c3bd/starknet_devnet/account.py#L35
        deployer_client = AccountClient(
            client=client,
            address=calculate_contract_address_from_hash(
                salt=20,
                class_hash=1803505466663265559571280894381905521939782500874858933595227108099796801620,
                constructor_calldata=[deployer_public_key],
                deployer_address=0,
            ),
            key_pair=KeyPair(
                private_key=deployer_private_key, public_key=deployer_public_key
            ),
            chain=StarknetChainId.TESTNET,
        )

        contract_addr = hex(await do_deploy(deployer_client, player_address))

        with open(f"/tmp/{ticket.team_id}", "w") as f:
            f.write(
                json.dumps(
                    {
                        "uuid": uuid,
                        "seed": seed,
                        "address": contract_addr,
                    }
                )
            )

        print()
        print(f"your private blockchain has been deployed")
        print(f"it will automatically terminate in 30 minutes")
        print(f"here's some useful information")
        print(f"uuid:           {uuid}")
        print(f"rpc endpoint:   http://{uuid}@{PUBLIC_IP}:{HTTP_PORT}")
        print(f"private key:    {hex(player_private_key)}")
        print(f"contract:       {contract_addr}")
        return 0

    return Action(name="launch new instance", handler=action)


def new_kill_instance_action():
    async def action() -> int:
        ticket = check_ticket(input("ticket please: "))
        if not ticket:
            print("invalid ticket!")
            return 1

        if ticket.challenge_id != CHALLENGE_ID:
            print("invalid ticket!")
            return 1

        data = requests.post(
            f"http://127.0.0.1:{HTTP_PORT}/kill",
            headers={
                "Authorization": f"Bearer {get_shared_secret()}",
                "Content-Type": "application/json",
            },
            data=json.dumps(
                {
                    "team_id": ticket.team_id,
                }
            ),
        ).json()

        print(data["message"])
        return 1

    return Action(name="kill instance", handler=action)


def new_get_flag_action(
    checker: Callable[[GatewayClient, int], bool],
):
    async def action() -> int:
        ticket = check_ticket(input("ticket please: "))
        if not ticket:
            print("invalid ticket!")
            return 1

        if ticket.challenge_id != CHALLENGE_ID:
            print("invalid ticket!")
            return 1

        try:
            with open(f"/tmp/{ticket.team_id}", "r") as f:
                data = json.loads(f.read())
        except:
            print("bad ticket")
            return 1

        # https://github.com/Shard-Labs/starknet-devnet/blob/660c0064b36a0eb4376ae7da38f2b8e8cb82f55e/starknet_devnet/accounts.py
        random_generator = random.Random()
        random_generator.seed(int(data["seed"]))

        deployer_private_key = random_generator.getrandbits(128)
        deployer_public_key = private_to_stark_key(deployer_private_key)

        player_private_key = random_generator.getrandbits(128)
        player_public_key = private_to_stark_key(player_private_key)
        player_address = calculate_contract_address_from_hash(
            salt=20,
            class_hash=1803505466663265559571280894381905521939782500874858933595227108099796801620,
            constructor_calldata=[player_public_key],
            deployer_address=0,
        )

        client = GatewayClient(f"http://{data['uuid']}@127.0.0.1:{HTTP_PORT}", TESTNET)
        # https://github.com/Shard-Labs/starknet-devnet/blob/a5c53a52dcf453603814deedb5091ab8c231c3bd/starknet_devnet/account.py#L35
        deployer_client = AccountClient(
            client=client,
            address=calculate_contract_address_from_hash(
                salt=20,
                class_hash=1803505466663265559571280894381905521939782500874858933595227108099796801620,
                constructor_calldata=[deployer_public_key],
                deployer_address=0,
            ),
            key_pair=KeyPair(
                private_key=deployer_private_key, public_key=deployer_public_key
            ),
            chain=StarknetChainId.TESTNET,
        )

        contract = await Contract.from_address(
            int(data["address"], 16), deployer_client
        )

        if not await checker(deployer_client, contract, player_address):
            print("are you sure you solved it?")
            return 1

        print(FLAG)
        return 0

    return Action(name="get flag", handler=action)


async def run_launcher_impl(actions: List[Action]):
    for i, action in enumerate(actions):
        print(f"{i+1} - {action.name}")

    action = int(input("action? ")) - 1
    if action < 0 or action >= len(actions):
        print("can you not")
        exit(1)

    exit(await actions[action].handler())


def run_launcher(actions: List[Action]):
    print("running until complete")
    asyncio.get_event_loop().run_until_complete(run_launcher_impl(actions))
