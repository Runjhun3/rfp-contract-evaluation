#!/usr/bin/env bash
# Runs ON the EC2 VM (Amazon Linux 2023) from the release folder, called by the
# GitHub Actions deploy job. Safe to run again: installs Docker only once.
set -euo pipefail

COMPOSE_VERSION=v2.29.7
BUILDX_VERSION=v0.17.1
PLUGINS=/usr/local/lib/docker/cli-plugins
cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null; then
  echo "== installing Docker"
  sudo dnf install -y docker
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER"
fi
if ! sudo docker compose version >/dev/null 2>&1; then
  echo "== installing docker compose $COMPOSE_VERSION and buildx $BUILDX_VERSION"
  sudo mkdir -p "$PLUGINS"
  sudo curl -fsSL -o "$PLUGINS/docker-compose" \
    "https://github.com/docker/compose/releases/download/$COMPOSE_VERSION/docker-compose-linux-x86_64"
  sudo curl -fsSL -o "$PLUGINS/docker-buildx" \
    "https://github.com/docker/buildx/releases/download/$BUILDX_VERSION/buildx-$BUILDX_VERSION.linux-amd64"
  sudo chmod +x "$PLUGINS/docker-compose" "$PLUGINS/docker-buildx"
fi

test -f .env || { echo ".env is missing next to docker-compose.prod.yml"; exit 1; }
compose() { sudo docker compose -f docker-compose.prod.yml "$@"; }

echo "== building images"
compose build
echo "== starting Postgres and applying migrations"
compose up -d --wait db
compose run --rm --no-deps api python run.py migrate
echo "== starting api, worker and web"
compose up -d --remove-orphans
sudo docker image prune -f >/dev/null

echo "== health check"
for _ in $(seq 1 30); do
  if curl -fsS http://localhost/api/v1/session >/dev/null; then
    compose ps
    echo "== deployed"
    exit 0
  fi
  sleep 2
done
compose logs --tail 50 api web
echo "== health check failed"
exit 1
