from discord.ext.commands import Bot, Cog
from discord_slash import cog_ext, SlashContext


class Core(Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(name="ping")
    async def _ping(self, ctx: SlashContext):
        await ctx.send(
            hidden=True, content=f"Pong! (`{round(self.bot.latency*1000)}`ms)"
        )


def setup(bot: Bot):
    bot.add_cog(Core(bot))
