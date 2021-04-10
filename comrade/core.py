import signal
import typing

import attr
import cattr
import toml

from discord.ext.commands import Bot as _Bot
from discord_slash import SlashCommand
from sqlalchemy.ext.asyncio import create_async_engine

from comrade import db


@attr.s(slots=True, auto_attribs=True)
class Config:

    token: str
    database: str
    extensions: typing.List[str] = attr.ib(factory=list)


class Bot(_Bot):
    def __init__(self, command_prefix="!", *args, config_file, **kwargs):
        super().__init__(command_prefix, *args, **kwargs)

        self._slash = SlashCommand(self, sync_commands=True)

        with open(config_file) as fp:
            self._config: Config = cattr.structure(toml.load(fp), Config)

        self.db = create_async_engine(self._config.database, echo=True)

        for ext in self._config.extensions:
            self.load_extension(ext, package="comrade.plugins")

    def reload(self):
        for ext in self._config.extensions:
            self.reload_extension(ext, package="comrade.plugins")

    def register_sighup(self):
        def handler(_signum, _frame):
            self.reload()

        signal.signal(signal.SIGHUP, handler)

    def run(self, token=None, *args, **kwargs):
        self.register_sighup()

        if token is None:
            token = self._config.token

        return super().run(token, *args, **kwargs)

    async def on_ready(self):
        async with self.db.begin() as conn:
            await conn.run_sync(db.metadata.create_all)
