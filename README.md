# route_time
Телеграмм-бот для расчета времени движения по маршруту с учетом пробок

В основе лежит сам бот для телеграмм, приложение Flask и Selenium для доступа к карте, mongo  в качестве хранилища

Все завернуто в docker для удобства

Для старта положить в корень проекта файл .secrets со следующим содержимым

```
ROUTE_TIME_BOT_TOKEN=<MEGA-SECRET-TOKEN>
ROUTE_TIME_YAMAPS_API_KEY=<MEGA-SECRET-API-KEY>
```
Запустить docker-compose

```bash
docker-compose up
```
