from PIL import Image


def safe(text):
    # TODO need implementation
    return text


def clear_keyboard(update):
    try:
        update.effective_message.edit_reply_markup(reply_markup=None)
    except AttributeError:
        update.effective_message.edit_message_reply_markup(reply_markup=None)


def routes_to_list(routes):
    result = []
    for n, r in enumerate(routes):
        _from = r.get("from_alias") or r.get("from_address")
        _to = r.get("to_alias") or r.get("to_address")
        result.append(f'{n+1}. {_from} -> {_to}')
    return result


def crop_by_element(element, input_file, output_file):
    """Обрезает скриншот по размерам элемента"""
    with Image.open(input_file) as img:
        left = element.location['x']
        top = element.location['y']
        right = left + element.size['width']
        bottom = top + element.size['height']

        img = img.crop((left, top, right, bottom))
        img.save(output_file, 'PNG')
        output_file.seek(0)
    return output_file


def pretty_time_delta(seconds):
    sign_string = '-' if seconds < 0 else ''
    seconds = abs(int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return '%s%d дней %d:%d' % (sign_string, days, hours, minutes)
    elif hours > 0:
        return '%s%d:%d' % (sign_string, hours, minutes)
    elif minutes > 0:
        return '%s%d мин' % (sign_string, minutes)



