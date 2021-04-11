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
    current: int
    earned: int
    spent: int
    adjustments: int


class DKPProvider:
    def __init__(self, config: DKPConfig):
        self.config = config
        self.db = create_async_engine(self.config.database, echo=True)

    async def current_dkp(self, character: str) -> typing.Optional[CharacterDKP]:
        url = "?".join(
            [
                urllib.parse.urljoin(self.config.url, "api.php"),
                urllib.parse.urlencode({"function": "points", "format": "json"}),
            ]
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        # The data structure returned by EQDKP is kind of wonky, what we're going
        # to have to do here is iterate over the dict fo players, ignoring the key
        # and look for a character named what we're looking for. If we don't find
        # one, then we just move on and return nothing.
        for player in data.get("players", {}).values():
            if player.get("name", "").lower() == character.lower():
                points = player["points"][f"multidkp_points:{self.config.dkp_pool_id}"]
                return CharacterDKP(
                    name=player["name"].lower(),
                    current=points["points_current"],
                    earned=points["points_earned"],
                    spent=points["points_spent"],
                    adjustments=points["points_adjustment"],
                )

        return None
