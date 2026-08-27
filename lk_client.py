"""Тонкий REST-клиент к CUBA REST v2 API проекта lk-tko-v2.

Конфигурация — только через переменные окружения (.env, см. .env.example):
LK_REST_BASE_URL, LK_REST_CLIENT_ID, LK_REST_CLIENT_SECRET,
LK_USERNAME, LK_PASSWORD.

Формат запросов подтверждён рабочими примерами из curls.txt в
репозитории lk-tko-v2 (OAuth2 password grant + generic entity search).
"""

import base64
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = os.environ.get("LK_REST_BASE_URL", "").rstrip("/")
_CLIENT_ID = os.environ.get("LK_REST_CLIENT_ID", "")
_CLIENT_SECRET = os.environ.get("LK_REST_CLIENT_SECRET", "")
_USERNAME = os.environ.get("LK_USERNAME", "")
_PASSWORD = os.environ.get("LK_PASSWORD", "")

_token_cache: dict = {"access_token": None, "expires_at": 0.0}

# Тестовый контур идёт через SSH-туннель до удалённой БД — httpx-дефолт
# в 5 секунд слишком мал даже для одиночных запросов.
_TIMEOUT = 30.0


def _require_config() -> None:
    missing = [
        name
        for name, value in [
            ("LK_REST_BASE_URL", _BASE_URL),
            ("LK_REST_CLIENT_ID", _CLIENT_ID),
            ("LK_REST_CLIENT_SECRET", _CLIENT_SECRET),
            ("LK_USERNAME", _USERNAME),
            ("LK_PASSWORD", _PASSWORD),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Не заданы переменные окружения: {', '.join(missing)}. "
            "Скопируй .env.example в .env и заполни реальными значениями."
        )


def _get_access_token() -> str:
    _require_config()

    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["access_token"]

    basic = base64.b64encode(f"{_CLIENT_ID}:{_CLIENT_SECRET}".encode()).decode()
    response = httpx.post(
        f"{_BASE_URL}/app/rest/v2/oauth/token",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "password",
            "username": _USERNAME,
            "password": _PASSWORD,
        },
        timeout=_TIMEOUT,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Не удалось получить access_token от lk-tko-v2 REST API: "
            f"{response.status_code} {response.text}"
        )

    payload = response.json()
    _token_cache["access_token"] = payload["access_token"]
    # небольшой запас на сетевые задержки перед истечением токена
    _token_cache["expires_at"] = time.time() + payload["expires_in"] - 30
    return _token_cache["access_token"]


def search_entity(entity: str, conditions: list[dict], view: str | None = None) -> list[dict]:
    """Найти сущности CUBA по условиям фильтра.

    entity — имя сущности вида "rtneo$Contragent".
    conditions — список условий CUBA REST filter, например:
        [{"property": "inn", "operator": "=", "value": "3800123123"}]
    """
    token = _get_access_token()
    body: dict = {"filter": {"conditions": conditions}}
    if view:
        body["view"] = view

    response = httpx.post(
        f"{_BASE_URL}/app/rest/v2/entities/{entity}/search",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=_TIMEOUT,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Ошибка запроса к lk-tko-v2 REST API ({entity}/search): "
            f"{response.status_code} {response.text}"
        )
    return response.json()


def call_v3(method: str, path: str, params: dict | None = None, json_body: dict | None = None):
    """Вызвать кастомный REST-контроллер lk-tko-v2 (/app/rest/v3/...).

    path начинается с "/", например "/debt/by-contragent".
    """
    token = _get_access_token()
    response = httpx.request(
        method,
        f"{_BASE_URL}/app/rest/v3{path}",
        headers={"Authorization": f"Bearer {token}"},
        params={k: v for k, v in (params or {}).items() if v is not None},
        json=json_body,
        timeout=_TIMEOUT,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Ошибка запроса к lk-tko-v2 REST API (v3{path}): "
            f"{response.status_code} {response.text}"
        )
    return response.json()


def call_service(service: str, method_name: str, params: dict):
    """Вызвать декларативный REST-сервис lk-tko-v2 (/app/rest/v2/services/...)."""
    token = _get_access_token()
    response = httpx.get(
        f"{_BASE_URL}/app/rest/v2/services/{service}/{method_name}",
        headers={"Authorization": f"Bearer {token}"},
        params={k: v for k, v in params.items() if v is not None},
        timeout=_TIMEOUT,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Ошибка запроса к lk-tko-v2 REST API (services/{service}/{method_name}): "
            f"{response.status_code} {response.text}"
        )
    return response.json()
