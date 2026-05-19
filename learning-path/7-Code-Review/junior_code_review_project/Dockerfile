FROM python:3.10-slim

WORKDIR /app

# Копируем только requirements для кэширования слоя
COPY prod_app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники
COPY prod_app/ ./prod_app/

EXPOSE 8000

CMD ["uvicorn", "prod_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
