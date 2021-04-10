import datetime
import string
import secrets

from discord.ext.commands import Cog
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType as OptionType
from discord_slash.utils.manage_commands import create_option
from sqlalchemy import Table, Column, Integer, String, DateTime, sql


from comrade import db


pending_claims = Table(
    "pending_claims",
    db.metadata,
    Column("id", Integer, primary_key=True),
    Column("claimed_on", DateTime, nullable=False, default=datetime.datetime.utcnow),
    Column(
        "discord_user",
        Integer,
        nullable=False,
        unique=True,
    ),
    Column("character", String(100), nullable=False),
    Column("code", String(10), nullable=False),
    extend_existing=True,
)


class DKP(Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_subcommand(
        base="dkp",
        name="link",
        description="Link your in-game character with your discord account",
        options=[
            create_option(
                name="character",
                description="character name to link",
                option_type=OptionType.STRING,
                required=True,
            )
        ],
    )
    async def _dkp_link(self, ctx: SlashContext, character):
        # Generate a unique 6 digit code to use to claim this character.
        code = "".join(secrets.choice(string.digits) for i in range(6))

        async with self.bot.db.begin() as tx:
            # If there is already an existing pending claim then we need to delete that row from the
            # database to make room for our new one.
            await tx.execute(
                sql.delete(pending_claims).where(
                    pending_claims.c.discord_user == ctx.author.id
                )
            )

            # Add a pending claim for this character, attached to this discord ID, using the
            # generated code from above.
            await tx.execute(
                sql.insert(pending_claims).values(
                    discord_user=ctx.author.id, character=character.lower(), code=code
                )
            )

        await ctx.send(
            content=(
                f"***Note: Linking a new character will remove any existing links!***\n\n"
                f"To finish linking {ctx.author.mention} to {character.title()}, "
                f"log into EverQuest and `/tell Comrade !link {code}` from {character.title()}."
            ),
            hidden=True,
        )
