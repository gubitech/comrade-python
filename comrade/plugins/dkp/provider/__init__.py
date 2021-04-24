import urllib.parse
import typing

import aiohttp
import attr

from sqlalchemy import Table, Column, Integer, String, DateTime, sql
from sqlalchemy.ext.asyncio import create_async_engine

from comrade.core import DKP as DKPConfig


@attr.s(slots=True, frozen=True, auto_attribs=True)
class CharacterDKP:

    name: str
    current: int = 0
    earned: int = 0
    spent: int = 0
    adjustments: int = 0


class DKPProvider:
    def __init__(self, config: DKPConfig):
        self.config = config
        self.db = create_async_engine(self.config.database, echo=True)

    async def list_dkp(self) -> typing.Mapping[str, CharacterDKP]:
        url = "?".join(
            [
                urllib.parse.urljoin(self.config.url, "api.php"),
                urllib.parse.urlencode({"function": "points", "format": "json"}),
            ]
        )

        # TODO: This shoudl have a persistent session, not throwing one away every
        #       time.
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        # The EQDKP data structure is kinda wonky and weird, we're going to massage
        # it into something that works better for us.
        # TODO: We filter our inactive and hidden people, is that right?
        pool_name = f"multidkp_points:{self.config.dkp_pool_id}"
        return {
            p["name"].lower(): CharacterDKP(
                name=p["name"].lower(),
                current=int(p["points"][pool_name]["points_current"]),
                earned=int(p["points"][pool_name]["points_earned"]),
                spent=int(p["points"][pool_name]["points_spent"]),
                adjustments=int(p["points"][pool_name]["points_adjustment"]),
            )
            for p in data.get("players", {}).values()
            if p["active"] == "1" and not p["hidden"]
        }

    async def current_dkp(self, character: str) -> typing.Optional[CharacterDKP]:
        return (await self.list_dkp()).get(character.lower(), None)
