# lk-tko-mcp

MCP-сервер (Model Context Protocol) на Python, который даёт Claude
инструментальный доступ к системе ЛК (личный кабинет, проект lk-tko-v2).

## Что это и зачем

MCP — открытый протокол, по которому внешний процесс отдаёт LLM набор
«инструментов» (tools): обычных функций с типизированными аргументами.
Подключив сервер к Claude Code, можно попросить Claude вызвать конкретную
функцию («получить статус контрагента по ИНН», «посчитать пени по периоду
для lkUser» и т.п.) вместо того, чтобы объяснять контекст текстом или
лезть в БД/код вручную каждый раз.

Цель пет-проекта — получить переиспользуемый инструментальный слой над
бизнес-логикой ЛК, которым можно пользоваться из любых будущих сессий
Claude Code, а не только внутри основного репозитория.

## Стек

- Python 3.10+, менеджер зависимостей — `uv`
- SDK: `mcp[cli]` (v2, пакет `mcp==2.1.0`), класс `mcp.server.MCPServer`
- Транспорт: stdio (Claude Code запускает процесс и общается с ним по stdin/stdout)

## Стек интеграции

Первый tool (`get_contragent_status`) ходит в **CUBA REST API v2**
lk-tko-v2 (OAuth2 password grant + generic entity search по
`rtneo$Contragent`) — не напрямую в БД. Формат запросов подтверждён
рабочими примерами из `curls.txt` репозитория lk-tko-v2.

## Структура

```
lk-tko-mcp/
├── server.py       # MCPServer + @mcp.tool() функции — вся логика инструментов
├── lk_client.py     # REST-клиент к lk-tko-v2 (OAuth2 + entity search)
├── run.py          # точка входа, которую регистрирует Claude Code
├── .env.example    # шаблон переменных окружения для доступа к ЛК (реальный .env не коммитится)
├── pyproject.toml
└── uv.lock
```

## Запуск и проверка локально

```bash
uv run mcp dev run.py   # открывает MCP Inspector в браузере — можно вручную вызывать tools
```

## Подключение к Claude Code

```bash
claude mcp add lk-tko-mcp -- uv run run.py
claude mcp list          # проверить, что статус Connected
```

## План разработки

1. **Каркас — готово.** Сервер с `ping` и `get_contragent_status`,
   запускается локально и через Inspector.
2. **REST-клиент — готово.** `lk_client.py`: OAuth2 password grant с
   кэшированием токена + `search_entity()` поверх CUBA REST v2.
3. **Первая настоящая интеграция — готово и проверено вживую.**
   `get_contragent_status` реально дёргает REST API lk-tko-v2 через
   `lk_client.search_entity("rtneo$Contragent", ...)`, проверено через
   MCP Inspector с реальными данными тестового контура.
4. **Подключение к Claude Code — готово.** `claude mcp add lk-tko-mcp -- uv run run.py`,
   статус `✔ Connected`. Гайд по разворачиванию для других разработчиков —
   см. `ONBOARDING.md`.
5. **Долг/биллинг (Приоритет 1 из RESEARCH.md) — готово, 6 из 7 проверены.**
   `get_contragent_debt`, `get_debt_by_phone`, `get_debt_by_email`,
   `get_serviced_periods`, `get_calculation_amount_type`, `get_contract`,
   `get_fine_details` — все реализованы через два новых REST-хелпера
   в `lk_client.py` (`call_v3` для кастомных v3-контроллеров, `call_service`
   для декларативных v2-сервисов). `get_contragent_bills` реализован, но
   заблокирован багом на стороне lk-tko-v2 (см. примечание ниже).
   `get_calculations_tabs`, `get_debt_breakdown_by_real_estate`,
   `find_contragents_with_debt_older_than` — **не реализованы**, у них нет
   REST-обёртки в lk-tko-v2 вообще (подтверждено grep по всему репозиторию).

## Известные проблемы

- **`get_contragent_bills` падает с 500.** Баг на стороне lk-tko-v2:
  `BillRepository.getBillsByContragentAndPeriod` (строка 71) ссылается на
  несуществующий алиас `b.documentNumber` вместо `e.documentNumber` —
  ломает JPQL-компиляцию при любом вызове `/app/rest/v3/bill`. Заведена
  отдельная задача на исправление в lk-tko-v2, наш код тут ни при чём.
5. **Расширение набора инструментов** — по одному инструменту на
   конкретный повторяющийся сценарий (например, период/пени для lkUser —
   см. память проекта `project_lk_user_config`), не абстрагировать заранее.
6. **(Опционально) командный доступ** — `claude mcp add lk-tko-mcp --scope project -- uv run run.py`
   создаст `.mcp.json` в репозитории, который можно закоммитить (без секретов).

## Проверка (после заполнения .env)

```bash
# 1. Юнит-уровень, без Claude
uv run python -c "from lk_client import search_entity; print(search_entity('rtneo$Contragent', [{'property':'inn','operator':'=','value':'<реальный ИНН>'}]))"

# 2. Через MCP Inspector
uv run mcp dev run.py

# 3. End-to-end
claude mcp add lk-tko-mcp -- uv run run.py
claude mcp list
```

## Примечания по безопасности

- `.env` не коммитится, реальные секреты (client_id/secret, логин/пароль)
  хранятся только локально.
- По умолчанию указывай локальный dev-инстанс lk-tko-v2
  (`http://localhost:8080`), а не staging/прод — там может быть
  неанонимизированный ПДн.
- У сущности `Contragent` нет заранее подтверждённого поля "статус" —
  `get_contragent_status` возвращает найденную сущность целиком, поле
  для реального статуса нужно определить по факту ответа REST API.
