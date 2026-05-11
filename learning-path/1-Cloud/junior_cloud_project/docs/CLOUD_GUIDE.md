# ☁️ Cloud Deployment Guide — AWS & GCP (для Junior-разработчиков)

> Этот гайд проведёт тебя от нуля до работающего сервера в облаке.  
> Выбери одну платформу: **AWS** или **GCP** — процесс похожий.

---

## 📋 Содержание

1. [Создание VM](#1-создание-vm)
2. [Настройка Firewall / Security Groups](#2-настройка-firewall--security-groups)
3. [SSH-ключи: генерация и подключение](#3-ssh-ключи-генерация-и-подключение)
4. [Установка Docker на Ubuntu](#4-установка-docker-на-ubuntu)
5. [Деплой приложения](#5-деплой-приложения)
6. [Проверка и отладка](#6-проверка-и-отладка)

---

## 1. Создание VM

### 🟠 AWS EC2

1. Войди на https://console.aws.amazon.com
2. В поиске набери **EC2** → нажми **Launch Instance**
3. Заполни форму:
   - **Name**: `junior-fastapi-server`
   - **AMI**: Ubuntu Server 22.04 LTS (Free tier eligible) ✅
   - **Instance type**: `t2.micro` (1 vCPU, 1 GB RAM) — бесплатный уровень
   - **Key pair**: нажми **Create new key pair**
     - Name: `junior-key`
     - Type: RSA
     - Format: `.pem`
     - Нажми **Create** — файл `junior-key.pem` скачается автоматически
4. В разделе **Network settings** → отметь **Allow HTTP traffic from the internet** ✅
5. Нажми **Launch Instance**
6. Подожди ~1 минуту → статус изменится на **Running**
7. Запомни **Public IPv4 address** (например: `54.123.45.67`)

### 🔵 GCP Compute Engine

1. Войди на https://console.cloud.google.com
2. Слева: **Compute Engine** → **VM instances** → **Create Instance**
3. Заполни форму:
   - **Name**: `junior-fastapi-server`
   - **Region**: выбери ближайший (например `us-central1`)
   - **Machine type**: `e2-micro` (2 vCPU, 1 GB RAM) — входит в бесплатный уровень
   - **Boot disk**: нажми **Change** → Ubuntu 22.04 LTS → **Select**
   - **Firewall**: отметь ✅ **Allow HTTP traffic** и ✅ **Allow HTTPS traffic**
4. Нажми **Create**
5. Дождись зелёной галочки → запомни **External IP**

---

## 2. Настройка Firewall / Security Groups

Нам нужно открыть два порта: **22 (SSH)** и **80 (HTTP)**.

### 🟠 AWS — Security Groups

1. В консоли EC2 → слева **Security Groups**
2. Найди группу, привязанную к твоему инстансу (обычно называется `launch-wizard-1`)
3. Вкладка **Inbound rules** → **Edit inbound rules** → **Add rule**:

   | Type  | Protocol | Port | Source    |
   |-------|----------|------|-----------|
   | SSH   | TCP      | 22   | My IP ✅  |
   | HTTP  | TCP      | 80   | 0.0.0.0/0 |

4. Нажми **Save rules**

> ⚠️ Для SSH рекомендуется ограничить источник своим IP (`My IP`), а не `0.0.0.0/0` — это безопаснее.

### 🔵 GCP — Firewall Rules

GCP автоматически создаёт правило для HTTP при включении галочки на шаге создания VM.  
Если нужно добавить вручную:

1. **VPC Network** → **Firewall** → **Create Firewall Rule**
2. Заполни:
   - **Name**: `allow-http`
   - **Direction**: Ingress
   - **Action**: Allow
   - **Targets**: All instances
   - **Source IP**: `0.0.0.0/0`
   - **Protocols and ports**: TCP → `80`
3. Нажми **Create**

SSH (порт 22) уже открыт по умолчанию в GCP через **Cloud Shell** или **Browser SSH**.

---

## 3. SSH-ключи: генерация и подключение

### Генерация ключей (если ещё нет)

Открой **Git Bash** (Windows) или **Terminal** (Mac/Linux):

```bash
# Генерируем пару ключей RSA
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
# Нажимай Enter на все вопросы (используем путь по умолчанию)
```

Ключи появятся здесь:
- Приватный: `~/.ssh/id_rsa` — **НИКОМУ НЕ ПОКАЗЫВАЙ**
- Публичный: `~/.ssh/id_rsa.pub` — этот можно размещать на серверах

### 🟠 Подключение к AWS EC2

```bash
# 1. Установи правильные права на скачанный .pem файл (только для Mac/Linux)
chmod 400 ~/Downloads/junior-key.pem

# 2. Подключись (замени IP на свой)
ssh -i ~/Downloads/junior-key.pem ubuntu@54.123.45.67
```

**Для Windows (Git Bash):**
```bash
ssh -i /c/Users/ИмяПользователя/Downloads/junior-key.pem ubuntu@54.123.45.67
```

### 🔵 Подключение к GCP

**Вариант 1 — Browser SSH** (самый простой):
В консоли GCP рядом с VM нажми кнопку **SSH** → откроется терминал прямо в браузере.

**Вариант 2 — через gcloud CLI:**
```bash
# Установи Google Cloud CLI: https://cloud.google.com/sdk/docs/install
gcloud compute ssh junior-fastapi-server --zone=us-central1-a
```

**Вариант 3 — стандартный SSH:**
```bash
# Добавь свой публичный ключ в GCP: Compute Engine → Metadata → SSH Keys
ssh -i ~/.ssh/id_rsa your_username@EXTERNAL_IP
```

---

## 4. Установка Docker на Ubuntu

Выполни эти команды **на сервере** (после подключения по SSH):

```bash
# Шаг 1: Обновить список пакетов
sudo apt-get update

# Шаг 2: Установить зависимости
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Шаг 3: Добавить официальный GPG-ключ Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Шаг 4: Добавить репозиторий Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Шаг 5: Установить Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Шаг 6: Добавить текущего пользователя в группу docker (чтобы не писать sudo каждый раз)
sudo usermod -aG docker $USER

# Шаг 7: Применить изменения группы БЕЗ перелогина
newgrp docker

# Шаг 8: Проверить установку
docker --version
docker compose version
```

Ожидаемый вывод:
```
Docker version 25.x.x, build ...
Docker Compose version v2.x.x
```

---

## 5. Деплой приложения

Теперь загрузим код на сервер и запустим его.

### Способ А — через Git (рекомендуется)

```bash
# На сервере:
sudo apt-get install -y git

git clone https://github.com/ТВО_ИМЯ/junior_cloud_project.git
cd junior_cloud_project

docker compose up -d
```

### Способ Б — через SCP (прямая загрузка файлов)

```bash
# На ЛОКАЛЬНОЙ машине (Git Bash / Terminal):
scp -i ~/Downloads/junior-key.pem -r ./junior_cloud_project ubuntu@54.123.45.67:~/

# Затем на сервере:
cd ~/junior_cloud_project
docker compose up -d
```

### Проверка запуска

```bash
# Посмотреть статус контейнеров
docker compose ps

# Логи в реальном времени
docker compose logs -f
```

---

## 6. Проверка и отладка

### Проверка работы API

Открой браузер и перейди по адресу:
```
http://ТВОЙ_ВНЕШНИЙ_IP
```

Ожидаемый ответ:
```json
{"status": "online"}
```

Или через curl (с локальной машины):
```bash
curl http://54.123.45.67
```

### Полезные команды для отладки

```bash
# Перезапустить контейнер
docker compose restart

# Остановить всё
docker compose down

# Пересобрать образ после изменений в коде
docker compose up -d --build

# Войти внутрь работающего контейнера
docker exec -it fastapi_app bash

# Посмотреть использование ресурсов
docker stats
```

### Типичные ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `Connection refused` | Порт 80 закрыт | Проверь Security Group / Firewall |
| `Permission denied (publickey)` | Неверный ключ или права | `chmod 400 key.pem` |
| `Port 80 is already in use` | Порт занят другим процессом | `sudo lsof -i :80` → завершить процесс |
| `docker: command not found` | Docker не установлен | Повтори шаг 4 |

---

## 🎉 Готово!

Твой FastAPI сервер работает в облаке. Следующие шаги для развития:

- [ ] Настроить доменное имя (Route 53 / Cloud DNS)
- [ ] Добавить HTTPS через Nginx + Let's Encrypt
- [ ] Настроить CI/CD через GitHub Actions
- [ ] Добавить мониторинг (Prometheus + Grafana)
