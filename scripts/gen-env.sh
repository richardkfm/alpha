#!/usr/bin/env bash
# Generate a .env with a random ALPHA_DB_PASSWORD, so the stack doesn't run
# on the docker-compose.yml default. Safe to re-run: leaves an existing .env
# (and any password already set in it) untouched.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -f .env ]; then
  cp .env.example .env
fi

if grep -q '^ALPHA_DB_PASSWORD=.\+' .env; then
  echo ".env already has ALPHA_DB_PASSWORD set — leaving it as is."
  exit 0
fi

password="$(openssl rand -base64 24)"
if grep -q '^ALPHA_DB_PASSWORD=' .env; then
  sed -i.bak "s|^ALPHA_DB_PASSWORD=.*|ALPHA_DB_PASSWORD=${password}|" .env
  rm -f .env.bak
else
  printf 'ALPHA_DB_PASSWORD=%s\n' "$password" >> .env
fi

echo "Generated a random ALPHA_DB_PASSWORD in .env."
