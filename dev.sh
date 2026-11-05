#!/bin/sh
set -eu

repo_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1
docker_smoke=false
for argument in "$@"; do
    if [ "$argument" = docker-smoke ]; then
        docker_smoke=true
        break
    fi
done
if [ -n "${SOLY_PYTHON:-}" ]; then
    python=$SOLY_PYTHON
elif [ "$docker_smoke" = false ] && [ -x "$repo_dir/.venv/bin/python" ]; then
    python=$repo_dir/.venv/bin/python
else
    python=''
    for candidate in python3.12 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            python=$candidate
            break
        fi
    done
fi
if [ -z "$python" ] || ! command -v "$python" >/dev/null 2>&1; then
    echo 'Python is missing. Install Python 3.12.15; set SOLY_PYTHON to its executable path.' >&2
    exit 1
fi
exec "$python" "$repo_dir/scripts/dev.py" "$@"
