import logging
import os

from telegram.ext import Updater, DictPersistence

logger = logging.getLogger(__name__)

try:
    token = os.environ['ROUTE_TIME_BOT_TOKEN']
except KeyError:
    message = 'You have to set ROUTE_TIME_BOT_TOKEN'
    logger.error(message)
    raise ValueError(message)


in_memory_persistence = DictPersistence(store_chat_data=False)


class RouteTimeBotUpdater(Updater):

    def register_handler(self, handler_cls, **kwargs):
        logger.debug('Add handler for {func.__name__}')
        dispatcher = self.dispatcher

        def decorator(func):
            handler = handler_cls(callback=func, **kwargs)
            dispatcher.add_handler(handler)
            return func

        return decorator


bot_updater = RouteTimeBotUpdater(token=token, use_context=True, persistence=in_memory_persistence)
