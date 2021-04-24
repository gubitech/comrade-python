from . import rpc
from .auction import Auction
from .dkp import DKP


def setup(bot):
    bot.add_cog(DKP(bot))
    bot.add_cog(Auction(bot))

    bot.add_rpc(*rpc.DKPService(bot))
    bot.add_rpc(*rpc.AuctionService(bot))
