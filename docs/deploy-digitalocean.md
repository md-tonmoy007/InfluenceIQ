# Deploying InfluenceIQ to a single DigitalOcean Droplet

One Droplet, one compose file, no managed services. Postgres, Redis, Qdrant,
and Caddy all run in containers; state lives in named volumes; you back up
the Droplet (snapshot) to recover.

## 1. Create the Droplet

- Ubuntu 24.04 LTS
- 4 GB / 2 vCPU / 80 GB SSD baseline (`s-2vcpu-4gb`) is a good starting point
- Add an A record for your domain (`app.example.com`) pointing at the Droplet's IP

## 2. Open the firewall

In the DO dashboard (**Networking → Firewalls**), or with `ufw` on the box:

```bash
ufw allow OpenSSH
ufw allow http
ufw allow https
ufw enable
```

Only 22, 80, 443 should be public.

## 3. Install Docker

```bash
apt update
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
   https://download.docker.com/linux/ubuntu $(. /etc/os/release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

## 4. Get the code and configure

```bash
git clone <your-repo-url> /opt/influenceiq
cd /opt/influenceiq

cp backend/.env.example backend/.env
$EDITOR backend/.env                 # set POSTGRES_PASSWORD, JWT_SECRET_KEY, API keys, etc.
$EDITOR infra/Caddyfile              # replace `app.example.com` with your domain
```

Required edits in `backend/.env`:
- `POSTGRES_PASSWORD` — strong random string; also update the same password inside `DATABASE_URL`
- `JWT_SECRET_KEY` — `openssl rand -hex 32`
- LLM / search / scraping API keys you actually use
- `FRONTEND_URL=https://app.example.com`

## 5. Build and start

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

That's the only command. It will:

- Build the backend, workers, and frontend images
- Pull postgres, redis, qdrant, and caddy
- Run Alembic migrations on first boot
- Start all services and tail logs

Watch the boot:

```bash
docker compose -f docker-compose.prod.yml logs -f
```

Caddy will request a Let's Encrypt cert on the first request to your domain.
After ~30 s, `https://app.example.com` should serve the app.

## 6. Updating

```bash
cd /opt/influenceiq
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

This rebuilds only changed images, recreates containers with zero source mounts
(the `volumes: !reset []` in the old merge file is gone — the new file has no
dev bind-mounts to begin with), runs Alembic migrations, and prunes nothing
automatically. To free disk:

```bash
docker image prune -f
docker builder prune -f --filter "until=24h"
```

## 7. Backups

The entire state of the app lives in named volumes on the Droplet:

| Volume         | Contents                       |
| -------------- | ------------------------------ |
| `postgres_data`| Postgres database              |
| `redis_data`   | Redis snapshots                |
| `qdrant_data`  | Qdrant vector index            |
| `caddy_data`   | TLS certs + ACME account       |
| `caddy_config` | Caddy runtime config           |

**Easiest**: turn on DO weekly Droplet snapshots (Dashboard → Droplet →
Backups → Enable). One snapshot captures all of the above.

**Hot snapshots** (no downtime):

```bash
# 1. Snapshot postgres with pg_dump
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "${POSTGRES_USER}" -Fc "${POSTGRES_DB}" \
  > /opt/backups/postgres-$(date +%F).dump

# 2. Snapshot redis with BGSAVE
docker compose -f docker-compose.prod.yml exec -T redis \
  sh -c 'redis-cli BGSAVE && tail -n1 -f /data/dump.rdb' &

# 3. Snapshot the qdrant_data volume to a tarball
docker run --rm \
  -v influenceiq_qdrant_data:/source:ro \
  -v /opt/backups:/dest \
  alpine tar czf /dest/qdrant-$(date +%F).tar.gz -C /source .
```

Wire those into a cron if you want them nightly.

## 8. Operations cheat sheet

```bash
# Status
docker compose -f docker-compose.prod.yml ps

# Logs (one service)
docker compose -f docker-compose.prod.yml logs -f --tail=200 backend-core

# Restart one service
docker compose -f docker-compose.prod.yml restart backend-core

# Shell into a container
docker compose -f docker-compose.prod.yml exec backend-core bash

# Run alembic migrations manually
docker compose -f docker-compose.prod.yml exec backend-core \
  alembic -c backend/alembic.ini upgrade head

# Reach Flower (Celery UI) over SSH tunnel
ssh -L 5555:localhost:5555 root@<host>
# then open http://localhost:5555
```

## 9. Teardown

```bash
# Stop and remove containers + networks (keeps volumes)
docker compose -f docker-compose.prod.yml down

# Stop AND wipe all data
docker compose -f docker-compose.prod.yml down -v
```

## 10. CI / auto-deploy (optional)

This guide is intentionally manual. If you later want push-to-deploy, the
shortest path is a GitHub Actions SSH step that runs:

```bash
cd /opt/influenceiq && git pull && \
  docker compose -f docker-compose.prod.yml up -d --build
```
