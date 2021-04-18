import hmac
import logging

from sqlalchemy import sql

from comrade.plugins.dkp.dkp import pending_claims, linked_characters

from . import auction_pb2_grpc, auction_pb2
from . import dkp_pb2_grpc, dkp_pb2


logger = logging.getLogger(__name__)


class Auction(auction_pb2_grpc.AuctionServicer):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot

    async def AddItem(self, request, context):
        auction = self.bot.get_cog("Auction")
        if auction is None:
            logger.warn(f"No auction cog found, discarding item: ")
        else:
            await auction.add_auction_item(
                request.item, request.quantity, request.added_by
            )

        return auction_pb2.AddItemResponse()


def AuctionService(*args, **kwargs):
    return (
        Auction(*args, **kwargs),
        auction_pb2.DESCRIPTOR.services_by_name["Auction"].full_name,
        auction_pb2_grpc.add_AuctionServicer_to_server,
    )


class DKP(dkp_pb2_grpc.DKPServicer):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot

    async def LinkCharacter(self, request, context):
        async with self.bot.db.begin() as tx:
            claim = (
                await tx.execute(
                    sql.select(pending_claims).where(
                        pending_claims.c.character == request.character.lower()
                    )
                )
            ).first()

            # We don't actually provide feedback to the API calls here, since
            # this is designed to be run from a program that just tails the
            # log file of an EverQuest client, so everything has to pass
            # silently.
            if claim is not None:
                claim = claim._mapping
                if hmac.compare_digest(request.code, claim["code"]):
                    # Go ahead and delete the claim from the database, since it's no
                    # longer pending, and will be made "real".
                    await tx.execute(
                        sql.delete(pending_claims).where(
                            pending_claims.c.id == claim["id"]
                        )
                    )

                    # We need to see if this character was already linked to
                    # another Discord account, if it was we're going to delete it.
                    await tx.execute(
                        sql.delete(linked_characters).where(
                            linked_characters.c.character == claim["character"]
                        )
                    )

                    # Finally, add our new linked character
                    await tx.execute(
                        sql.insert(linked_characters).values(
                            discord_user=claim["discord_user"],
                            character=claim["character"],
                        )
                    )

        return dkp_pb2.LinkCharacterResponse()


def DKPService(*args, **kwargs):
    return (
        DKP(*args, **kwargs),
        dkp_pb2.DESCRIPTOR.services_by_name["DKP"].full_name,
        dkp_pb2_grpc.add_DKPServicer_to_server,
    )
