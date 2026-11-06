#!/usr/bin/env bash
# Throwaway Odoo sandbox on the local doodba stack: clone a real DB, run the
# CURRENT worktree's code against the clone (install, shell, HTTP server), then
# clean up. The source DB and the user's own runtime container are never
# touched: everything runs in one-off `docker compose run` containers with the
# worktree mounted read-only over /opt/odoo/custom/src/kmitl.
#
# Usage:  odoo_sandbox.sh <command> [args...]
#   dbs                                   list databases with sizes
#   sql     <db> <query>                  run a READ-ONLY query (any db)
#   clone   <src_db> <dst_db>             copy src -> dst, then neutralize dst
#   neutralize <db> [worktree]            `odoo neutralize`: no mail, no crons
#   install <db> <mod1,mod2> [worktree]   -i modules, --stop-after-init
#   update  <db> <mod1,mod2> [worktree]   -u modules (cascades to dependents!)
#   shell   <db> <script.py> [worktree]   pipe a script into `odoo shell`
#   serve   <db> [port] [worktree]        detached HTTP server, waits until up
#   stop    [port]                        remove the server container
#   drop    <db>                          DROP DATABASE
# Every command that writes to or runs Odoo on a db refuses names that don't
# start with the sandbox prefix; only `dbs` and `sql` read other databases.
#
# Env overrides: ODOO_COMPOSE_DIR (doodba project dir, default
#                ~/Workspace/kmitl-odoo), ODOO_DB_CONTAINER (default: the
#                project's running `db` service), ODOO_DB_USER,
#                ODOO_SANDBOX_PREFIX (default "sbx_").
set -euo pipefail

COMPOSE_DIR="${ODOO_COMPOSE_DIR:-$HOME/Workspace/kmitl-odoo}"
DB_USER="${ODOO_DB_USER:-odoo}"
PREFIX="${ODOO_SANDBOX_PREFIX:-sbx_}"
MOUNT_POINT="/opt/odoo/custom/src/kmitl"
ADDONS_PATH="$MOUNT_POINT,/opt/odoo/auto/addons"

die() { echo "odoo_sandbox: $*" >&2; exit 1; }

[ -f "$COMPOSE_DIR/devel.yaml" ] ||
    die "no devel.yaml in '$COMPOSE_DIR'; set ODOO_COMPOSE_DIR to your kmitl-odoo checkout"

# The container name depends on the folder the stack was cloned into, so ask
# compose for it instead of assuming "kmitl-odoo-db-1".
db_container() {
    local c="${ODOO_DB_CONTAINER:-}"
    [ -n "$c" ] || c="$(cd "$COMPOSE_DIR" && docker compose -f devel.yaml ps -q db 2>/dev/null)"
    [ -n "$c" ] || die "postgres is not running; start it with: cd $COMPOSE_DIR && docker compose -f devel.yaml up -d db"
    echo "$c"
}

worktree_of() {
    local wt="${1:-}"
    [ -n "$wt" ] || wt="$(git rev-parse --show-toplevel 2>/dev/null)" ||
        die "not in a git worktree; pass the worktree path explicitly"
    [ -d "$wt" ] || die "worktree '$wt' does not exist"
    (cd "$wt" && pwd)
}

psql_admin() {
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -c "$1"
}

db_exists() {
    [ "$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -tAc \
        "select 1 from pg_database where datname = '$1'")" = 1 ]
}

# One-off odoo container running the worktree's code. Extra args go to `odoo`.
# Tracing is off so sandbox runs don't show up as "kmitl-erp" in shared Grafana.
odoo_run() {
    local wt="$1"; shift
    (cd "$COMPOSE_DIR" && docker compose -f devel.yaml run --rm --no-deps -T \
        -e DKN_OTEL_ENABLE=false \
        -v "$wt:$MOUNT_POINT:ro" odoo odoo "$@" --addons-path="$ADDONS_PATH")
}

require_sandbox_name() {
    case "$1" in
        "$PREFIX"*) ;;
        *) die "refusing: '$1' does not start with '$PREFIX' (sandbox DBs only)" ;;
    esac
}

port_in_use() { (echo >"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

cmd="${1:-}"; shift || true
case "$cmd" in stop|"") ;; *) DB_CONTAINER="$(db_container)" ;; esac
case "$cmd" in
    dbs)
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d postgres -tAc \
            "select datname, pg_size_pretty(pg_database_size(datname))
             from pg_database where not datistemplate order by 1"
        ;;
    sql)
        [ $# -eq 2 ] || die "usage: sql <db> <query>"
        # Read-only session: safe to point at the source DB before cloning.
        docker exec -e PGOPTIONS="-c default_transaction_read_only=on" "$DB_CONTAINER" \
            psql -U "$DB_USER" -d "$1" -v ON_ERROR_STOP=1 -c "$2"
        ;;
    clone)
        [ $# -eq 2 ] || die "usage: clone <src_db> <dst_db>"
        require_sandbox_name "$2"
        db_exists "$1" || die "source db '$1' does not exist (see: dbs)"
        ! db_exists "$2" || die "'$2' already exists; drop it or pick another name"
        # TEMPLATE is instant but needs no other session on the source. A
        # running odoo keeps idle connections to every db, so it usually
        # fails; never kill those sessions, fall back to a dump instead.
        if psql_admin "CREATE DATABASE \"$2\" TEMPLATE \"$1\"" >/dev/null 2>&1; then
            echo "cloned $1 -> $2 (template)"
        else
            echo "template copy blocked (source in use); dumping instead, ~1 min per GB..."
            psql_admin "CREATE DATABASE \"$2\" OWNER \"$DB_USER\"" >/dev/null
            # pg_restore exits non-zero on a few harmless errors (unaccent
            # trigram indexes), so judge the copy by its content instead.
            docker exec "$DB_CONTAINER" sh -c \
                "pg_dump -U '$DB_USER' -Fc '$1' | pg_restore -U '$DB_USER' -d '$2' --no-owner" \
                >"/tmp/odoo_sandbox_${2}_clone.log" 2>&1 || true
            n="$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$2" -tAc \
                "select count(*) from ir_module_module where state = 'installed'" 2>/dev/null || echo 0)"
            if [ "${n:-0}" -eq 0 ]; then
                psql_admin "DROP DATABASE IF EXISTS \"$2\" WITH (FORCE)" >/dev/null
                die "restore failed (log: /tmp/odoo_sandbox_${2}_clone.log)"
            fi
            echo "cloned $1 -> $2 (dump, $n modules installed)"
        fi
        # The filestore is not copied, so the cached asset bundles point to
        # missing files and every page 500s; drop them so odoo rebuilds them.
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$2" -qc \
            "delete from ir_attachment where res_model = 'ir.ui.view' and url like '/web/assets/%'"
        # A copy of prod would otherwise mail real staff and run real crons.
        "$0" neutralize "$2"
        ;;
    neutralize)
        [ $# -ge 1 ] || die "usage: neutralize <db> [worktree]"
        require_sandbox_name "$1"
        wt="$(worktree_of "${2:-}")"
        odoo_run "$wt" neutralize -d "$1" >"/tmp/odoo_sandbox_${1}_neutralize.log" 2>&1 ||
            { tail -20 "/tmp/odoo_sandbox_${1}_neutralize.log"; die "neutralize failed"; }
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$1" -tAc \
            "select 'neutralized: ' || coalesce((select value from ir_config_parameter
                    where key = 'database.is_neutralized'), 'NO')
             || ', active crons: ' || (select count(*) from ir_cron where active)
             || ', active mail servers: ' || (select string_agg(smtp_host, ',')
                    from ir_mail_server where active)"
        ;;
    install|update)
        [ $# -ge 2 ] || die "usage: $cmd <db> <modules> [worktree]"
        require_sandbox_name "$1"
        flag="-i"; [ "$cmd" = update ] && flag="-u"
        wt="$(worktree_of "${3:-}")"
        log="/tmp/odoo_sandbox_${1}_${cmd}.log"
        odoo_run "$wt" -d "$1" "$flag" "$2" --stop-after-init --without-demo=all \
            >"$log" 2>&1 || { tail -40 "$log"; die "$cmd failed (full log: $log)"; }
        echo "$cmd ok (log: $log)"
        # The log usually holds pre-existing drift noise; the module states
        # below are the real verdict.
        mods="'$(echo "$2" | sed "s/,/','/g")'"
        docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$1" -tAc \
            "select name || ': ' || state from ir_module_module where name in ($mods) order by name"
        echo "--- ERROR lines in log (often unrelated drift; check if they name your modules):"
        grep -E " (ERROR|CRITICAL) |Traceback" "$log" | head -10 || true
        ;;
    shell)
        [ $# -ge 2 ] || die "usage: shell <db> <script.py> [worktree]"
        require_sandbox_name "$1"
        [ -f "$2" ] || die "script '$2' not found"
        wt="$(worktree_of "${3:-}")"
        # Odoo logs to the same stream; drop INFO/WARNING noise, keep prints.
        odoo_run "$wt" shell -d "$1" --no-http <"$2" 2>&1 |
            grep -vE "^[0-9-]+ [0-9:,]+ [0-9]+ (INFO|WARNING|DEBUG) |^doodba INFO|level=warning|^ ?Container |pkg_resources|^  import pkg_resources"
        ;;
    serve)
        [ $# -ge 1 ] || die "usage: serve <db> [port] [worktree]"
        require_sandbox_name "$1"
        port="${2:-18069}"
        wt="$(worktree_of "${3:-}")"
        name="odoo_sandbox_$port"
        docker rm -f "$name" >/dev/null 2>&1 || true
        port_in_use "$port" && die "port $port is already in use (another sandbox or service); pick another"
        # The server joins a non-internal network below, so refuse a db that
        # could still mail real people.
        [ "$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$1" -tAc \
            "select count(*) from ir_config_parameter
             where key = 'database.is_neutralized' and value ilike 'true'")" = 1 ] ||
            die "'$1' is not neutralized; run: $0 neutralize $1"
        # No cron threads: modules installed after neutralize may re-enable
        # their own crons.
        (cd "$COMPOSE_DIR" && docker compose -f devel.yaml run -d --name "$name" --no-deps \
            -e DKN_OTEL_ENABLE=false \
            -p "127.0.0.1:$port:8069" -v "$wt:$MOUNT_POINT:ro" odoo odoo \
            -d "$1" --db-filter="^$1\$" --addons-path="$ADDONS_PATH" \
            --workers=0 --max-cron-threads=0 --http-port=8069) >/dev/null 2>&1
        # Docker publishes no ports for a container on internal networks only,
        # and doodba's `default` is internal unless DOODBA_NETWORK_INTERNAL=false.
        # Join a bridge of our own: doodba's `public` only exists while a proxy
        # service is up, and its name depends on the compose project.
        docker network inspect odoo_sandbox_public >/dev/null 2>&1 ||
            docker network create odoo_sandbox_public >/dev/null
        docker network connect odoo_sandbox_public "$name" || {
            docker rm -f "$name" >/dev/null 2>&1
            die "could not attach $name to network odoo_sandbox_public"
        }
        for _ in $(seq 1 60); do
            [ "$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null)" = true ] || break
            code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/web/login" || true)"
            [ "$code" = 200 ] && { echo "up: http://127.0.0.1:$port (container $name)"; exit 0; }
            sleep 3
        done
        docker logs --tail 30 "$name" >&2
        die "server did not come up on port $port"
        ;;
    stop)
        port="${1:-18069}"
        docker rm -f "odoo_sandbox_$port" >/dev/null && echo "stopped odoo_sandbox_$port"
        ;;
    drop)
        [ $# -eq 1 ] || die "usage: drop <db>"
        require_sandbox_name "$1"
        psql_admin "DROP DATABASE IF EXISTS \"$1\" WITH (FORCE)" && echo "dropped $1"
        ;;
    *)
        sed -n '2,25p' "$0"; exit 1 ;;
esac
