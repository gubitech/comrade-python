from comrade.core import Bot

import logging

logging.basicConfig(level=logging.INFO)


bot = Bot(config_file="comrade.toml")
bot.run()
