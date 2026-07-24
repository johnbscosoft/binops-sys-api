docker run -d \
  --name postgresdb \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=admin123 \
  -e POSTGRES_DB=mydatabase \
  -p 5432:5432 \
  postgres

## Project structure

This API uses a feature-based structure. Each feature owns its route handlers,
Pydantic schemas, and SQLAlchemy models.

```text
app/
  main.py
  app.py
  database.py
  core/
    config.py
  api/
    router.py
  features/
    questions/
      model.py
      schema.py
      router.py
    users/
      model.py
      schema.py
      router.py
```

Run locally:

```bash
uvicorn app.main:app --reload
```

API routes are mounted under `/api/v1`.

## CI/CD and production deployment

Pushes to `main` and `testenv` run API tests, build a production Docker image,
and publish it to `jbscosoft/binops-sys-api` on Docker Hub. See
[`DEPLOYMENT.md`](DEPLOYMENT.md) for GitHub secret setup, server deployment,
immutable tags, health checks, database changes, and rollback instructions.


sh -c 'pids=$(lsof -tiTCP:8001 -sTCP:LISTEN); [ -z "$pids" ] || kill -9 $pids; exec uv run main.py'

sh -c 'pids=$(lsof -tiTCP:8001 -sTCP:LISTEN); [ -z "$pids" ] || kill -9 $pids;'
