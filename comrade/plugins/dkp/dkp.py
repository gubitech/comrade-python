import datetime
import string
import secrets
import typing

from discord.ext.commands import Cog
from discord_slash import cog_ext, SlashContext
from discord_slash.model import SlashCommandOptionType as OptionType
from discord_slash.utils.manage_commands import create_option
from sqlalchemy import Table, Column, Integer, String, DateTime, sql


from comrade import db
from comrade.plugins.dkp.provider import DKPProvider


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


linked_characters = Table(
    "linked_characters",
    db.metadata,
    Column("id", Integer, primary_key=True),
    Column("claimed_on", DateTime, nullable=False, default=datetime.datetime.utcnow),
    Column(
        "discord_user",
        Integer,
        nullable=False,
        unique=True,
    ),
    Column("character", String(100), nullable=False, unique=True),
    extend_existing=True,
)


class DKP(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.provider = DKPProvider(self.bot.config.dkp)

    async def get_character(self, user_id: int) -> typing.Optional[str]:
        async with self.bot.db.begin() as tx:
            linked = (
                await tx.execute(
                    sql.select(linked_characters).where(
                        linked_characters.c.discord_user == user_id
                    )
                )
            ).first()

        if linked is None:
            return None

        return linked._mapping["character"]

    @cog_ext.cog_subcommand(
        base="dkp",
        name="check",
        description="Check someone's current DKP",
        options=[
            create_option(
                name="user",
                description="which discord user's dkp to check if other than own",
                option_type=OptionType.USER,
                required=False,
            ),
        ],
    )
    async def _dkp_check(self, ctx: SlashContext, user=None):
        # We have to defer the response, because fetching resutls might take > 3s and then
        # our interaction will expire.
        await ctx.defer(hidden=True)

        # If we weren't given a user, then we're using the current user.
        if user is None:
            user = ctx.author

        character = await self.get_character(user.id)

        # If the given user does not have a linked character, then we can't look up
        # their DKP, and we should bail out with an error.
        if character is None:
            await ctx.send(
                content=f"***Error:*** {user.mention} does not have a linked character.",
                hidden=True,
            )
            return

        # We have a character name now, so we'll look up their DKP using our DKP Provider.
        dkp = await self.provider.current_dkp(character)
        if dkp is None:
            # If we weren't able to locate a character in the DKP system, then that's also
            # an error we need to bail out with.
            await ctx.send(
                content=(
                    f"***Error:*** {character.title()} does not appear in "
                    f"the DKP system, have they ever earned any DKP?"
                ),
                hidden=True,
            )
            return

        # Finally, we actually have the data to return the actual results.
        # Embed's cannot currently be hidden, but they intended to allow them, once
        # they do, we can switch to using something like this for embeds.
        # embed = discord.Embed(title="DKP Stats", description="Foobar", color=0x00FF00)
        # embed.add_field(name="DKP", value="17")
        await ctx.send(
            content=f"**{dkp.name.title()} ({user.mention})**:\n\nCurrent: {dkp.current}",
            hidden=True,
        )

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
