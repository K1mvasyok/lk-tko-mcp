"""MCP-сервер lk-tko-mcp.

Предоставляет Claude инструменты (tools) для работы с системой ЛК
(личный кабинет). Каждый @mcp.tool() — это функция, которую Claude
может вызвать сам во время диалога, если решит, что она нужна.

Запуск для разработки (с инспектором в браузере):
    uv run mcp dev server.py

Прямой запуск (то, что использует Claude Code как stdio-транспорт):
    uv run server.py
"""

from mcp.server import MCPServer

import lk_client

mcp = MCPServer("lk-tko-mcp")


@mcp.tool()
def ping() -> str:
    """Проверка того, что сервер жив и подключён."""
    return "pong from lk-tko-mcp"


@mcp.tool()
def get_contragent_status(inn: str) -> dict:
    """Найти контрагента ЛК по ИНН и вернуть его данные.

    Возвращает найденную сущность Contragent целиком через REST API
    lk-tko-v2 — отдельного поля "статус" может не быть, это нужно
    смотреть по реальным данным, которые вернёт CUBA REST.
    """
    results = lk_client.search_entity(
        "rtneo$Contragent",
        [{"property": "inn", "operator": "=", "value": inn}],
    )
    if not results:
        return {"inn": inn, "found": False}
    return {"inn": inn, "found": True, "contragent": results[0]}


if __name__ == "__main__":
    mcp.run()
