# 🚀 Junior Cloud Project — FastAPI + Docker

Минимальный FastAPI-сервер, готовый к запуску в облаке одной командой.

---

## ⚡ Быстрый старт (локально)

```bash
docker-compose up -d        # собрать образ и запустить контейнер
curl http://localhost       # ожидаемый ответ: {"status":"online"}
docker-compose logs -f      # следить за логами
docker-compose down         # остановить
```

---

## 🖥️ Hardware Requirements (рекомендации для локальной разработки)

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| CPU       | Intel Core i5-10300H (4 ядра / 8 потоков) | i7 / Ryzen 7 |
| RAM       | 8 GB    | **16 GB**     |
| GPU VRAM  | —       | **4 GB** (для ML-экспериментов) |
| Диск      | 20 GB SSD | 50 GB SSD  |
| ОС        | Ubuntu 20.04+ / macOS 12+ / Windows 10+ (WSL2) | Ubuntu 22.04 LTS |

> 💡 Для запуска только Docker + FastAPI хватит 2 GB RAM.  
> 16 GB рекомендуется, если планируешь добавлять ML-модели или тяжёлые зависимости.

---

## 📁 Структура проекта

```
junior_cloud_project/
├── app/
│   └── main.py          # FastAPI приложение
├── config/              # место для .env, конфигов (пока пустая)
├── docs/                # место для документации API
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .gitignore
├── README.md
└── CLOUD_GUIDE.md       # пошаговый гайд по деплою в AWS / GCP
```

---

## ☁️ Деплой в облако

Читай [`CLOUD_GUIDE.md`](CLOUD_GUIDE.md) — там всё по шагам для новичка.
