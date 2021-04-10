from .dkp import DKP


def setup(bot):
    bot.add_cog(DKP(bot))
