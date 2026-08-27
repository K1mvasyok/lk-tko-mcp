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


@mcp.tool()
def get_contragent_debt(pa_or_inn: str) -> dict:
    """Долг контрагента (основной долг, пени, госпошлина) по лицевому счёту или ИНН."""
    return lk_client.call_v3("POST", "/debt/by-contragent", json_body={"paOrInn": pa_or_inn})


@mcp.tool()
def get_debt_by_phone(phone: str) -> dict:
    """Долг по всем лицевым счетам, привязанным к телефону."""
    return lk_client.call_v3("POST", "/debt/by-phone", json_body={"phone": phone})


@mcp.tool()
def get_debt_by_email(email: str) -> dict:
    """Долг по всем лицевым счетам, привязанным к email."""
    return lk_client.call_v3("POST", "/debt/by-email", json_body={"email": email})


@mcp.tool()
def get_serviced_periods(pa_or_inn: str) -> dict:
    """Периоды обслуживания (даты начала/окончания) лицевого счёта или ИНН."""
    return lk_client.call_v3("POST", "/debt/serviced-period", json_body={"paOrInn": pa_or_inn})


@mcp.tool()
def get_calculation_amount_type(pa_or_inn: str) -> dict:
    """Тип расчёта начислений и текущий долг по лицевому счёту/ИНН."""
    return lk_client.call_v3("POST", "/debt/calculation-amount-type", json_body={"paOrInn": pa_or_inn})


@mcp.tool()
def get_contragent_bills(
    contragent_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
    is_paid: bool | None = None,
) -> dict:
    """Счета контрагента за период.

    contragent_id — UUID контрагента (см. поле "id" в get_contragent_status).
    date_from/date_to — даты в формате dd.MM.yyyy.
    """
    return lk_client.call_v3(
        "GET",
        "/bill",
        params={
            "currentContragentId": contragent_id,
            "from": date_from,
            "to": date_to,
            "isPaid": is_paid,
        },
    )


@mcp.tool()
def get_contract(contragent_id: str) -> list:
    """Список договоров контрагента с суммами начислений/платежей/пеней/долга.

    contragent_id — UUID контрагента (см. поле "id" в get_contragent_status).
    """
    return lk_client.call_service(
        "rtneo_ApiRestService", "getContract", {"contragentId": contragent_id}
    )


@mcp.tool()
def get_fine_details(personal_account: str, date_from: str, date_to: str) -> dict:
    """Детализация пеней по лицевому счёту за период, по договорам и месяцам.

    date_from/date_to — даты в формате dd.MM.yyyy.
    """
    return lk_client.call_service(
        "rtneo_ApiRestService",
        "getFineContragentByPeriod",
        {"personalAccount": personal_account, "from": date_from, "to": date_to},
    )


if __name__ == "__main__":
    mcp.run()
