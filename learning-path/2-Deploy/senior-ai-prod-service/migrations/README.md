# Migrations

This project uses `init_db()` (SQLAlchemy `create_all`) for fast local setup.

## Upgrade to Alembic (production recommendation)

```bash
pip install alembic
alembic init migrations
# Edit alembic.ini: sqlalchemy.url = ${DATABASE_URL}
# Edit migrations/env.py: target_metadata = Base.metadata

alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```
