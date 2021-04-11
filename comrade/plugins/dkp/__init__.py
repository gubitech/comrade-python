from . import rpc
from .dkp import DKP


def setup(bot):
    bot.add_cog(DKP(bot))

    bot.add_rpc(*rpc.DKPService(bot))
