"""Модуль содержит бизнес-логику бота"""
import functools
import logging
from io import BytesIO

import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from .utils import crop_by_element

logger = logging.getLogger(__name__)

MAP_SERVICE_URL = 'http://nginx'
CHROME_URL = 'http://chrome:4444'


def request_exception_handler(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        try:
            result, error = func(*args, **kwargs)
            return result, error
        except requests.exceptions.RequestException:
            msg = 'Сервис недоступен 😲'
            logger.warning(msg, exc_info=True)
            return None, msg

    return decorator


@request_exception_handler
def list_routes(user_id):
    response = requests.get(MAP_SERVICE_URL + '/api/routes', params=dict(user_id=user_id))
    logger.debug(response.json())
    response_data = response.json()
    if response_data.get('error') == 'Not found' or len(response_data['result']['routes']) == 0:
        return [], 'Нет сохраненных маршрутов'
    return response_data['result']['routes'], None


@request_exception_handler
def add_route(user_id, from_address, to_address, from_alias='', to_alias=''):
    response = requests.post(
        f'http://nginx/api/routes',
        data=dict(
            user_id=user_id,
            from_address=from_address,
            from_alias=from_alias,
            to_address=to_address,
            to_alias=to_alias,
        ),
    )
    response_data = response.json()
    if not response_data.get('ok'):
        logger.error(response.json())
        return None, 'Ошибка'
    logger.debug(response.json())
    return response_data['result']['routeID'], None


@request_exception_handler
def del_route(route_id):
    response = requests.delete(MAP_SERVICE_URL + f'/api/routes/{route_id}')
    response_data = response.json()
    if not response_data.get('ok'):
        logger.error(response.json())
        return None, 'Ошибка'
    logger.debug(response.json())
    return int(response_data['result']['deletedCount']), None


def get_route(user_id, route_idx):
    routes, error = list_routes(user_id)
    if error:
        return None, error
    try:
        choosed_route = routes[route_idx]
        logger.debug('Choosed route %s ', choosed_route)
    except IndexError:
        choosed_route = None
        error = 'Ошибка'
    return choosed_route, error


class RouteTime(object):
    def __init__(self, route_id, is_reversed=False):
        self._route_id = route_id
        self._is_reversed = is_reversed

    def __enter__(self, *args, **kwargs):
        options = Options()
        options.add_argument("--window-size=800x600")
        options.headless = True
        self._driver = webdriver.Remote(
            command_executor=CHROME_URL + '/wd/hub',
            desired_capabilities=webdriver.DesiredCapabilities.CHROME,
            options=options
        )
        self._map_screenshot = BytesIO()
        return self

    def __exit__(self, *args, **kwargs):
        self._driver.quit()
        self._map_screenshot.close()

    def run(self):
        url = MAP_SERVICE_URL + f'/map?route_id={self._route_id}&is_reversed={int(self._is_reversed)}'
        self._driver.get(url)
        try:
            # Время маршрута
            route_time = WebDriverWait(self._driver, 15).until(
                EC.presence_of_element_located((By.ID, "routeTimeSeconds"))
            ).text
            route_time = float(route_time)

            # Скриншот маршрута
            with BytesIO(self._driver.get_screenshot_as_png()) as screenshot:
                map_element = self._driver.find_element_by_id('map')
                crop_by_element(map_element, screenshot, self._map_screenshot)
            error = None
        except TimeoutException:
            logger.error(f'Requested resource {url}', exc_info=True)
            return None, None, 'Сервис недоступен 😲'

        return route_time, self._map_screenshot
