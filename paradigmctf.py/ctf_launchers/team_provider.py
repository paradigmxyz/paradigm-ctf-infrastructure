import abc
import os
from dataclasses import dataclass
from typing import Optional

import requests


class TeamProvider(abc.ABC):
    @abc.abstractmethod
    def get_team(self) -> Optional[str]:
        pass


class TicketTeamProvider(TeamProvider):
    @dataclass
    class Ticket:
        challenge_id: str
        team_id: str

    def __init__(self, challenge_id):
        self.__challenge_id = challenge_id

    def get_team(self):
        ticket = self.__check_ticket(input("ticket? "))
        if not ticket:
            print("invalid ticket!")
            return None

        if ticket.challenge_id != self.__challenge_id:
            print("invalid ticket!")
            return None

        return ticket.team_id

    def __check_ticket(self, ticket: str) -> Ticket:
        ticket_info = requests.post(
            "https://ctf.paradigm.xyz/api/internal/check-ticket",
            json={
                "ticket": ticket,
            },
        ).json()
        if not ticket_info["ok"]:
            return None

        return TicketTeamProvider.Ticket(
            challenge_id=ticket_info["ticket"]["challengeId"],
            team_id=ticket_info["ticket"]["teamId"],
        )


class StaticTeamProvider(TeamProvider):
    def __init__(self, team_id, ticket):
        self.__team_id = team_id
        self.__ticket = ticket

    def get_team(self) -> str | None:
        ticket = input("ticket? ")

        if ticket != self.__ticket:
            print("invalid ticket!")
            return None

        return self.__team_id


class LocalTeamProvider(TeamProvider):
    def __init__(self, team_id):
        self.__team_id = team_id

    def get_team(self):
        return self.__team_id


def get_team_provider() -> TeamProvider:
    env = os.getenv("ENV", "local")
    if env == "local":
        return LocalTeamProvider(team_id="local")
    elif env == "dev":
        return StaticTeamProvider(team_id="dev", ticket="dev2023")
    else:
        return TicketTeamProvider(challenge_id=os.getenv("CHALLENGE_ID"))
