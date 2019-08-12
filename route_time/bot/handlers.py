import functools
import logging
import re

from telegram import InlineKeyboardButton as button, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ConversationHandler, Filters, MessageHandler

from . import services
from .bot_updater import bot_updater
from .utils import clear_keyboard, pretty_time_delta, routes_to_list, safe

logger = logging.getLogger(__name__)

CHOOSE_ROUTE, ADD_ROUTE, ADD_FROM, ALIAS_FROM, ADD_TO, ALIAS_TO, DELETE_ROUTE = range(7)

dispatcher = bot_updater.dispatcher


def log(func):
    current_logger = logging.getLogger(func.__module__)

    @functools.wraps(func)
    def decorator(self, *args, **kwargs):
        current_logger.debug('Enter %s', func.__name__)
        result = func(self, *args, **kwargs)
        current_logger.debug(result)
        current_logger.debug('Exit %s', func.__name__)
        return result

    return decorator


@log
def start(update, context):
    keyboard = [['Маршруты'], ['Помощь']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    update.effective_message.reply_text(
        'Привет! Я умею сохранять ваши маршруты и показывать время проезда с учетом пробок',
        reply_markup=reply_markup
    )
    return CHOOSE_ROUTE


@log
def help_me(update, context):
    update.effective_message.reply_text(
        'Тут будет помощь, но позже. А пока живите с этим ))',
    )
    return CHOOSE_ROUTE


@log
def manage_routes(update, context):

    context.user_data.clear()
    user_id = update.effective_user.id

    routes, error = services.list_routes(user_id)
    if error and routes is None:
        update.effective_message.reply_text(error)
        return

    keyboard = []
    if routes:
        for i, route in enumerate(routes, start=1):
            keyboard.append([
                button(text=f'{i}->', callback_data=f'{i}_there'),
                button(text=f'<-{i}', callback_data=f'{i}_back')
            ])
        keyboard.append([button(text='Добавить маршрут', callback_data='add')])
        keyboard.append([button(text='Удалить маршрут', callback_data='del')])
        update.effective_message.reply_text('Выберите маршрут')
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.effective_message.reply_text('\n'.join(routes_to_list(routes)), reply_markup=reply_markup)
    else:
        keyboard.append([button(text='Добавить маршрут', callback_data='add')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.effective_message.reply_text('Нет сохраненных маршрутов. Добавить?', reply_markup=reply_markup)
    return CHOOSE_ROUTE


@log
def choose_route_to_del(update, context):
    user_id = update.effective_user.id

    routes, error = services.list_routes(user_id)
    if error:
        update.effective_message.reply_text(error)
        return
    keyboard = [[button(text=f'Удалить! {i} ', callback_data=f'{i}_del')] for i, route in enumerate(routes, start=1)]
    keyboard.append([button(text='Отмена', callback_data='cancel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.effective_message.reply_text(
        'Какой маршрут удалить?\n' + '\n'.join(routes_to_list(routes)),
        reply_markup=reply_markup
    )
    return DELETE_ROUTE


@log
def show_route(update, context):
    clear_keyboard(update)

    idx, direction = update.callback_query.data.split('_')
    route_idx = int(idx) - 1
    is_reversed = direction == 'back'

    user_id = update.effective_user.id

    choosed_route, error = services.get_route(user_id, route_idx)
    if error:
        update.effective_message.reply_text(error)
        return

    with services.RouteTime(choosed_route['_id'], is_reversed=is_reversed) as rt:
        route_time_seconds, map_screenshot, error = rt.run()
        if error:
            update.effective_message.reply_text(error)
            return
        route_time = pretty_time_delta(route_time_seconds)
        from_ = choosed_route.get('from_alias') or choosed_route.get('from_address')
        to_ = choosed_route.get('to_alias') or choosed_route.get('to_address')
        if is_reversed:
            from_, to_ = to_, from_
        update.effective_message.reply_text(
            f'Маршрут: {from_} -> {to_}\n'
            f'Дорога займет {route_time}'
        )
        update.effective_message.reply_photo(map_screenshot)
    return ConversationHandler.END


@log
def del_route(update, context):
    clear_keyboard(update)

    user_id = update.effective_user.id
    route_idx = int(update.callback_query.data.split('_')[0]) - 1

    choosed_route, error = services.get_route(user_id, route_idx)
    if error:
        update.effective_message.reply_text(error)
        return

    _, error = services.del_route(choosed_route['_id'])
    if error:
        update.effective_message.reply_text(error)
        return

    return manage_routes(update, context)


@log
def add_route(update, context):
    keyboard = [[button(text='Отмена', callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.effective_message.reply_text('Введите адрес отправления', reply_markup=reply_markup)
    return ADD_FROM


@log
def add_from_address(update, context):
    context.user_data['from_address'] = safe(update.effective_message.text)
    keyboard = [[button(text='Отмена', callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.effective_message.reply_text('Введите короткое название\nНапример: Дом или 🏠', reply_markup=reply_markup)
    return ALIAS_FROM


@log
def add_from_alias(update, context):
    context.user_data['from_alias'] = safe(update.effective_message.text)
    keyboard = [[button(text='Отмена', callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Введите адрес назначения', reply_markup=reply_markup)
    return ADD_TO


@log
def add_to_address(update, context):
    context.user_data['to_address'] = safe(update.effective_message.text)
    keyboard = [[button(text='Отмена', callback_data='cancel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Введите короткое название, например: Работа или 🏢', reply_markup=reply_markup)
    return ALIAS_TO


@log
def add_to_alias(update, context):
    user_data = context.user_data
    user_id = update.message.from_user.id
    user_data['to_alias'] = safe(update.effective_message.text)

    logger.debug(f'user_id: {user_id}, username: {update.effective_user.username}, data: {user_data}')

    from_ = user_data.get('from_alias') or user_data.get('from_address')
    to_ = user_data.get('to_alias') or user_data.get('to_address')

    _, error = services.add_route(user_id, **user_data)
    if error:
        update.effective_message.reply_text(error)
        return

    update.message.reply_text(f'Добавлен маршрут\n{from_} -> {to_} ')
    return manage_routes(update, context)


@log
def cancel(update, context):
    clear_keyboard(update)
    update.effective_message.reply_text('Отменено')
    context.user_data.clear()
    return manage_routes(update, context)


@log
def fallback(update, context):
    context.user_data.clear()
    update.effective_message.reply_text('Упс, ошибочка вышла.')
    return CHOOSE_ROUTE


start_filter = Filters.regex(re.compile('(^/start$)|(^начать$)', re.IGNORECASE))
start_handler = MessageHandler(start_filter, start)

help_filter = Filters.regex(re.compile(r'(^/help$)|(^помощь$)', re.IGNORECASE))
help_handler = MessageHandler(help_filter, help_me)

manage_routes_filter = Filters.regex(re.compile(r'маршруты', re.IGNORECASE))
manage_routes_handler = MessageHandler(manage_routes_filter, manage_routes)

none_state_handler = MessageHandler(Filters.all, manage_routes)

add_route_handler = CallbackQueryHandler(add_route, pattern=r'^add$')
add_from_address_handler = MessageHandler(Filters.text, add_from_address)
add_from_alias_handler = MessageHandler(Filters.text, add_from_alias)
add_to_address_handler = MessageHandler(Filters.text, add_to_address)
add_to_alias_handler = MessageHandler(Filters.text, add_to_alias)

del_handler = CallbackQueryHandler(choose_route_to_del, pattern=r'^del$')
show_route_handler = CallbackQueryHandler(show_route, pattern=r'^(\d)+_(there|back)$')
del_route_handler = CallbackQueryHandler(del_route, pattern=r'^(\d)+_del$')
cancel_handler = CallbackQueryHandler(cancel, pattern=r'^cancel$')

states = {
    CHOOSE_ROUTE: [show_route_handler, add_route_handler, del_handler],
    ADD_FROM: [add_from_address_handler, cancel_handler],
    ALIAS_FROM: [add_from_alias_handler, cancel_handler],
    ADD_TO: [add_to_address_handler, cancel_handler],
    ALIAS_TO: [add_to_alias_handler, cancel_handler],
    DELETE_ROUTE: [del_route_handler, cancel_handler],
}

conv_handler = ConversationHandler(
    entry_points=[manage_routes_handler],
    states=states,
    fallbacks=[MessageHandler(None, fallback)]
)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(help_handler)
dispatcher.add_handler(conv_handler)

dispatcher.add_error_handler(fallback)
