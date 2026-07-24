# API Docker Hub deployment

The CI workflow tests the API, builds the production image, and publishes it to:

```text
jbscosoft/binops-sys-api
```

## Docker Hub and GitHub setup

1. Create `jbscosoft/binops-sys-api` in Docker Hub.
2. Create a Docker Hub access token with read/write access to that repository.
3. In the GitHub repository, open **Settings → Secrets and variables → Actions**.
4. Create the repository secret `DOCKERHUB_TOKEN`.

The workflow publishes:

- `latest` for pushes to `main`.
- `main` or `testenv` for pushes to those branches.
- `sha-<commit>` for an immutable deployment and rollback reference.
- semantic-version tags when a tag such as `v1.2.0` is pushed.

Pull requests run tests and compile checks, but do not publish images.

## Prepare the server

Copy these files to a deployment directory on the server:

```text
compose.server.yaml
deploy/api.env.example
```

Create the production environment file:

```bash
cp deploy/api.env.example deploy/api.env
chmod 600 deploy/api.env
```

Replace every placeholder in `deploy/api.env`. Do not commit `deploy/api.env`.

For a private Docker Hub repository, sign in with a read-only access token:

```bash
docker login --username jbscosoft
```

## Deploy the latest main image

```bash
API_IMAGE_TAG=latest docker compose -f compose.server.yaml pull
API_IMAGE_TAG=latest docker compose -f compose.server.yaml up -d --remove-orphans
docker compose -f compose.server.yaml ps
```

The API is bound to `127.0.0.1:8001` by default for use behind Nginx, Caddy, or
Traefik. Set `API_BIND_ADDRESS=0.0.0.0` only when the port must be exposed
directly and is protected by a firewall.

## Deploy an immutable commit image

Use the short commit SHA shown in the GitHub Actions build:

```bash
API_IMAGE_TAG=sha-a82db73 docker compose -f compose.server.yaml pull
API_IMAGE_TAG=sha-a82db73 docker compose -f compose.server.yaml up -d
```

Persist the selected tag in a server-only `.env` file to keep it across commands:

```env
API_IMAGE_TAG=sha-a82db73
```

## Roll back

Set `API_IMAGE_TAG` to the previous known-good SHA tag, then pull and recreate:

```bash
docker compose -f compose.server.yaml pull
docker compose -f compose.server.yaml up -d
```

## Database changes

Apply reviewed SQL files from `migrations/manual/` before switching the API to a
version that requires them. Keep a database backup and do not run unreviewed
schema changes automatically from the application container.

## Verification

```bash
curl --fail http://127.0.0.1:8001/health
docker inspect --format '{{.State.Health.Status}}' binops-sys-api
docker compose -f compose.server.yaml logs --tail=100 api
```
