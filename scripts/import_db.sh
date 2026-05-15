#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DUMP_DIR="$PROJECT_DIR/dump"

if docker compose version >/dev/null 2>&1; then
	DC=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
	DC=(docker-compose)
else
	echo "Error: neither 'docker compose' nor 'docker-compose' is available."
	exit 1
fi

IN_FILE="${1:-}"

if [[ -z "$IN_FILE" ]]; then
	if [[ -d "$DUMP_DIR" ]]; then
		IN_FILE="$(find "$DUMP_DIR" -maxdepth 1 -type f -name 'odoo_backup_*.dump' | sort | tail -n 1 || true)"
	fi
	if [[ -z "$IN_FILE" ]]; then
		echo "No backup provided and no dump found in $DUMP_DIR"
		exit 1
	fi
fi

if [[ ! -f "$IN_FILE" ]]; then
	echo "File not found: $IN_FILE"
	exit 1
fi

FS_FILE="${IN_FILE%.dump}_filestore.tar.gz"
FS_BASENAME="$(basename "$FS_FILE")"

cd "$PROJECT_DIR"

echo "Stopping web container..."
"${DC[@]}" stop web

echo "Starting db container..."
"${DC[@]}" up -d db

echo "Recreating database..."
"${DC[@]}" exec -T db dropdb -U odoo --if-exists sukha_final
"${DC[@]}" exec -T db createdb -U odoo sukha_final

echo "Restoring database from: $IN_FILE"
"${DC[@]}" exec -T db pg_restore -U odoo -d sukha_final --no-owner --clean --if-exists < "$IN_FILE"

if [[ -f "$FS_FILE" ]]; then
	echo "Restoring filestore from: $FS_FILE"
	"${DC[@]}" run --no-deps --rm -v odoo-web-data:/filestore alpine sh -c "
		set -e
		rm -rf /filestore/* /filestore/.[!.]* /filestore/..?*
		tar xzf \"/backup/$FS_BASENAME\" -C /filestore
		fs_base=/filestore/.local/share/Odoo/filestore
		if [ -d \"\$fs_base/postgres\" ]; then
			mkdir -p \"\$fs_base/sukha_final\"
			cp -a \"\$fs_base/postgres/.\" \"\$fs_base/sukha_final/\"
		fi
	"
else
	echo "Warning: No filestore backup found at $FS_FILE, skipping."
fi

echo "Starting full stack..."
"${DC[@]}" up -d db web

echo "Done. Database imported."
