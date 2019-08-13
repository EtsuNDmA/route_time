import logging

from route_time.bot.handlers import *
from route_time.bot.updater import bot_updater

# TODO move to config
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    bot_updater.start_polling()
    bot_updater.idle()
