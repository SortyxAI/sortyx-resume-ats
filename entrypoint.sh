#!/usr/bin/env sh
set -e

# If secret files are mounted into separate directories, expose them at the expected app paths.
if [ -e "/run/secrets/token/token.json" ] && [ ! -e "/app/token.json" ]; then
    ln -sf "/run/secrets/token/token.json" "/app/token.json"
fi

if [ -e "/run/secrets/client/client_secrets1.json" ] && [ ! -e "/app/client_secrets1.json" ]; then
    ln -sf "/run/secrets/client/client_secrets1.json" "/app/client_secrets1.json"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 9000
