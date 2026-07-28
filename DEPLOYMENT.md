# API Docker Hub build and manual production deployment

GitHub Actions runs tests, builds the production API image, and publishes it to:

```text
jbscosoft/binops-sys
```

Production deployment is intentionally manual. GitHub Actions does not connect
to the production server.

## GitHub Actions and Docker Hub

Create the GitHub repository secret:

```text
DOCKERHUB_TOKEN
```

It must contain a Docker Hub access token with read/write permission for the
shared `jbscosoft/binops-sys` repository.

The workflow publishes:

- `api-latest` for pushes to `main`.
- `api-main` and `api-testenv` for their respective branches.
- `api-sha-<full-commit>` as an immutable deployment and rollback tag.
- API-prefixed semantic-version tags such as `api-1.2.0`.

The shared repository can also contain tags such as `ui-latest`,
`ui-sha-<commit>`, and `db-18.4` without requiring separate Docker Hub
repositories.

Pull requests run tests without publishing an image. Pushes to `main` or
`testenv` run tests and publish images, but never deploy to the server.

## Files required on the production server

Place these files in `/opt/binops-sys-api`:

```text
compose.server.yaml
deploy/api.env
```

Prepare the directory:

```bash
sudo mkdir -p /opt/binops-sys-api/deploy
sudo chown -R "$USER":"$USER" /opt/binops-sys-api
cd /opt/binops-sys-api
chmod 600 deploy/api.env
```

The production environment should include:

```env
ENVIRONMENT=production
AUTO_CREATE_TABLES=false
DATABASE_URL=postgresql://admin:YOUR_URL_ENCODED_PASSWORD@database:5432/wasteops_db
CORS_ORIGINS=https://erisa.binopsug.com
JWT_SECRET_KEY=REPLACE_WITH_A_LONG_RANDOM_SECRET
```

Retain the remaining OTP, SMTP, Twilio, token-expiry, and authentication values
from `deploy/api.env.example`. Never commit `deploy/api.env`.

## Shared Docker network

The API and PostgreSQL containers communicate through the external network
`binops_backend`. Create it once:

```bash
docker network inspect binops_backend >/dev/null 2>&1 \
  || docker network create binops_backend
```

Both the API and database Compose files must declare this external network.
PostgreSQL must have the network alias `database`.

Verify:

```bash
docker network inspect binops_backend \
  --format '{{range .Containers}}{{.Name}} → {{.IPv4Address}}{{println}}{{end}}'
```

## Docker Hub login on the server

For a private repository, use a read-only Docker Hub token:

```bash
docker login --username jbscosoft
```

## Manual production deployment

First confirm the desired image exists in Docker Hub. Prefer the immutable SHA
tag shown in the successful GitHub Actions run.

Create `/opt/binops-sys-api/.deploy.env`:

```env
API_IMAGE_TAG=api-sha-REPLACE_WITH_FULL_COMMIT
```

Deploy:

```bash
cd /opt/binops-sys-api

docker compose \
  --env-file .deploy.env \
  -f compose.server.yaml \
  pull api

docker compose \
  --env-file .deploy.env \
  -f compose.server.yaml \
  up -d --remove-orphans api
```

The API listens on port `8001` inside its container and is published only on:

```text
127.0.0.1:9001
```

Caddy can therefore proxy `/api/*` to `127.0.0.1:9001`, while port `9001`
remains unavailable externally.

## Deploy `api-latest`

For a simple manual deployment of the latest API image from `main`:

```bash
cd /opt/binops-sys-api
API_IMAGE_TAG=api-latest docker compose -f compose.server.yaml pull api
API_IMAGE_TAG=api-latest docker compose -f compose.server.yaml up -d --remove-orphans api
```

Immutable SHA tags are recommended because they provide an exact rollback target.

## Verification

Check the container and API:

```bash
docker compose -f compose.server.yaml ps
docker inspect --format '{{.State.Health.Status}}' binops-sys-api
curl --fail http://127.0.0.1:9001/health
docker compose -f compose.server.yaml logs --tail=100 api
```

Check Docker DNS and PostgreSQL connectivity:

```bash
docker exec binops-sys-api \
  python -c "import socket; print(socket.gethostbyname('database'))"

docker exec binops-sys-api \
  python -c "import socket; connection=socket.create_connection(('database',5432),5); print('Database TCP connection successful'); connection.close()"
```

## Database migrations

Back up PostgreSQL before applying schema changes. Apply only reviewed migration
files required by the version being deployed. Do not automatically run
unreviewed migrations from the API container.

## Manual rollback

Put the previous known-good tag in `.deploy.env`:

```env
API_IMAGE_TAG=api-sha-PREVIOUS_FULL_COMMIT
```

Then pull and recreate:

```bash
cd /opt/binops-sys-api
docker compose --env-file .deploy.env -f compose.server.yaml pull api
docker compose --env-file .deploy.env -f compose.server.yaml up -d api
curl --fail http://127.0.0.1:9001/health
```
