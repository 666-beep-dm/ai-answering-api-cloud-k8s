"""
Тесты для учебного стенда.
Запуск: pytest tests/ -v
"""
import pytest
from httpx import AsyncClient, ASGITransport

import os


@pytest.mark.asyncio
async def test_get_users_bug_mode():
    """
    В BUG_MODE _process_users_buggy должен бросать KeyError.
    ASGITransport (тестовый клиент) не перехватывает глобальный
    exception_handler FastAPI, поэтому проверяем сам факт выброса.
    В реальном uvicorn-сервере global_exception_handler превратит
    это исключение в HTTP 500 с JSON-телом.
    """
    os.environ["BUG_MODE"] = "true"
    import importlib
    import app.main as main_module
    importlib.reload(main_module)

    # Прямая проверка: вспомогательная функция бросает KeyError
    with pytest.raises(KeyError, match="email"):
        await main_module._process_users_buggy(main_module.FAKE_DB_BUGGY)

    # Через HTTP-клиент ожидаем либо 500, либо пробрасывание KeyError
    try:
        async with AsyncClient(
            transport=ASGITransport(app=main_module.app), base_url="http://test"
        ) as client:
            response = await client.get("/users")
        assert response.status_code == 500
    except KeyError:
        pass  # ASGITransport пробросил исключение — это тоже корректное поведение


@pytest.mark.asyncio
async def test_get_users_fixed_mode():
    """В FIXED MODE ожидаем 200 и список пользователей."""
    os.environ["BUG_MODE"] = "false"
    import importlib
    import app.main as main_module
    importlib.reload(main_module)

    async with AsyncClient(
        transport=ASGITransport(app=main_module.app), base_url="http://test"
    ) as client:
        response = await client.get("/users")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    for user in data["users"]:
        assert "email" in user


@pytest.mark.asyncio
async def test_health():
    """Health-check всегда возвращает 200."""
    import importlib
    import app.main as main_module
    importlib.reload(main_module)

    async with AsyncClient(
        transport=ASGITransport(app=main_module.app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
