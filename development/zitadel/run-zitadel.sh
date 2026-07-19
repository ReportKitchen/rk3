#!/bin/bash
# ZITADEL launcher (dev box): pulls secrets from /var/www/rk3/.env and runs
# start-from-init (idempotent: init + setup + serve). Used by zitadel.service.
set -euo pipefail
ENVFILE=/var/www/rk3/.env
get() { grep "^$1=" "$ENVFILE" | head -1 | cut -d= -f2-; }

export ZITADEL_DATABASE_POSTGRES_USER_PASSWORD="$(get ZITADEL_DB_PASSWORD)"
export ZITADEL_DATABASE_POSTGRES_ADMIN_PASSWORD="$(get ZITADEL_DB_PASSWORD)"
export ZITADEL_FIRSTINSTANCE_ORG_HUMAN_PASSWORD="$(get ZITADEL_ADMIN_PASSWORD)"

exec /usr/local/bin/zitadel start-from-init \
  --config /var/www/rk3/development/zitadel/zitadel-config.yaml \
  --steps /var/www/rk3/development/zitadel/zitadel-steps.yaml \
  --masterkey "$(get ZITADEL_MASTERKEY)"
