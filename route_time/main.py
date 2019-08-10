import logging

from route_time.bot import bot_updater

logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    bot_updater.start_polling()
    bot_updater.idle()
