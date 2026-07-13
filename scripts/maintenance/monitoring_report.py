#!/usr/bin/env python3
"""
Relatorio periodico de monitoramento do PostgreSQL (Coleta Premiada - Core).

Consulta pg_stat_statements, pg_stat_activity, pg_stat_database e pg_locks
e gera um relatorio em texto/JSON com as metricas mais relevantes.

Uso:
    python monitoring_report.py                  # stdout (texto)
    python monitoring_report.py --json           # saida JSON
    python monitoring_report.py --json --output /tmp/report.json
    python monitoring_report.py --slow-ms 500    # queries > 500ms
    python monitoring_report.py --top-n 20       # top 20 queries

Agendamento via cron (exemplo, todo dia as 07:00):
    0 7 * * * python /scripts/monitoring_report.py --json --output /var/log/reports/daily_$(date +\%Y\%m\%d).json

Dependencias: psycopg2 (ou psycopg2-binary)
    pip install psycopg2-binary
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERRO: psycopg2 nao encontrado. Instale com: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def connect() -> psycopg2.extensions.connection:
    """Conecta ao PostgreSQL usando variaveis de ambiente (estilo Docker Compose)."""
    return psycopg2.connect(
        host=get_env("PGHOST", "core-db"),
        port=get_env("PGPORT", "5432"),
        user=get_env("PGUSER", "postgres"),
        password=get_env("PGPASSWORD", ""),
        dbname=get_env("PGDATABASE", "coleta_premiada"),
        connect_timeout=10,
    )


def fetch_rows(conn: psycopg2.extensions.connection, query: str, params: tuple | None = None) -> list[dict]:
    """Executa uma query e retorna os resultados como lista de dicionarios."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, params)
        return list(cur.fetchall())


def fetch_scalar(conn: psycopg2.extensions.connection, query: str) -> Any:
    """Executa uma query e retorna um unico valor escalar."""
    with conn.cursor() as cur:
        cur.execute(query)
        row = cur.fetchone()
        return row[0] if row else None


# ─── Funcoes de coleta de metricas ───────────────────────────────────────────

def collect_database_stats(conn: psycopg2.extensions.connection) -> dict:
    """Metricas do banco de dados via pg_stat_database."""
    rows = fetch_rows(conn, """
        SELECT
            datname,
            numbackends AS conexoes_ativas,
            xact_commit  AS transacoes_commit,
            xact_rollback AS transacoes_rollback,
            blks_read     AS blocos_lidos_disco,
            blks_hit      AS blocos_hit_cache,
            tup_returned  AS tuplas_retornadas,
            tup_fetched   AS tuplas_buscadas,
            tup_inserted  AS tuplas_inseridas,
            tup_updated   AS tuplas_atualizadas,
            tup_deleted   AS tuplas_deletadas,
            conflicts     AS conflitos_replicacao,
            deadlocks     AS deadlocks,
            temp_files    AS arquivos_temp,
            temp_bytes    AS bytes_temp,
            blk_read_time AS tempo_leitura_disco_ms,
            blk_write_time AS tempo_escrita_ms
        FROM pg_stat_database
        WHERE datname NOT IN ('template0', 'template1')
          AND datname IS NOT NULL
        ORDER BY numbackends DESC
    """)
    return {"databases": rows, "collected_at": datetime.now(timezone.utc).isoformat()}


def collect_top_queries(
    conn: psycopg2.extensions.connection,
    top_n: int = 15,
    min_mean_ms: float = 1.0,
) -> list[dict]:
    """Top queries por tempo medio de execucao via pg_stat_statements."""
    return fetch_rows(conn, """
        SELECT
            queryid,
            LEFT(query, 500) AS query_truncada,
            calls,
            ROUND(mean_exec_time::numeric, 2) AS tempo_medio_ms,
            ROUND(total_exec_time::numeric, 2) AS tempo_total_ms,
            ROUND(min_exec_time::numeric, 2) AS tempo_min_ms,
            ROUND(max_exec_time::numeric, 2) AS tempo_max_ms,
            ROUND(stddev_exec_time::numeric, 2) AS desvio_padrao_ms,
            rows,
            shared_blks_hit AS cache_hits,
            shared_blks_read AS cache_misses,
            CASE
                WHEN shared_blks_hit + shared_blks_read > 0
                THEN ROUND(100.0 * shared_blks_hit / (shared_blks_hit + shared_blks_read), 1)
                ELSE NULL
            END AS taxa_cache_pct
        FROM pg_stat_statements
        WHERE mean_exec_time >= %(min_ms)s
          AND query !~* '(pg_stat|pg_catalog|information_schema|pg_stat_statements)'
        ORDER BY mean_exec_time DESC
        LIMIT %(limit)s
    """, {"min_ms": min_mean_ms, "limit": top_n})


def collect_connections(conn: psycopg2.extensions.connection) -> list[dict]:
    """Conexoes ativas com detalhes de estado e duracao."""
    return fetch_rows(conn, """
        SELECT
            pid,
            usename  AS usuario,
            application_name AS app,
            client_addr AS ip_cliente,
            state AS estado,
            wait_event_type AS tipo_espera,
            wait_event AS evento_espera,
            EXTRACT(epoch FROM (NOW() - query_start))::int AS duracao_query_seg,
            EXTRACT(epoch FROM (NOW() - xact_start))::int AS duracao_transacao_seg,
            EXTRACT(epoch FROM (NOW() - backend_start))::int AS duracao_conexao_seg,
            LEFT(query, 300) AS query_truncada
        FROM pg_stat_activity
        WHERE state IS NOT NULL
          AND pid <> pg_backend_pid()
        ORDER BY
            CASE state
                WHEN 'active' THEN 0
                WHEN 'idle in transaction' THEN 1
                WHEN 'idle in transaction (aborted)' THEN 2
                ELSE 3
            END,
            query_start ASC NULLS LAST
    """)


def collect_locks(conn: psycopg2.extensions.connection) -> list[dict]:
    """Locks que estao bloqueando outras transacoes."""
    return fetch_rows(conn, """
        SELECT
            blocked_locks.pid     AS pid_bloqueado,
            blocking_locks.pid    AS pid_bloqueador,
            blocked_activity.usename AS usuario_bloqueado,
            blocking_activity.usename AS usuario_bloqueador,
            blocked_activity.query AS query_bloqueada,
            blocking_activity.query AS query_bloqueadora,
            EXTRACT(epoch FROM (NOW() - blocked_locks.granted))::int AS duracao_lock_seg,
            blocked_locks.mode    AS modo_lock,
            blocked_locks.locktype AS tipo_lock,
            blocked_locks.relation::regclass::text AS relacao
        FROM pg_catalog.pg_locks blocked_locks
        JOIN pg_catalog.pg_locks blocking_locks
            ON blocked_locks.locktype = blocking_locks.locktype
            AND blocked_locks.database IS NOT DISTINCT FROM blocking_locks.database
            AND blocked_locks.relation IS NOT DISTINCT FROM blocking_locks.relation
            AND blocked_locks.page IS NOT DISTINCT FROM blocking_locks.page
            AND blocked_locks.tuple IS NOT DISTINCT FROM blocking_locks.tuple
            AND blocked_locks.virtualxid IS NOT DISTINCT FROM blocking_locks.virtualxid
            AND blocked_locks.transactionid IS NOT DISTINCT FROM blocking_locks.transactionid
            AND blocked_locks.classid IS NOT DISTINCT FROM blocking_locks.classid
            AND blocked_locks.objid IS NOT DISTINCT FROM blocking_locks.objid
            AND blocked_locks.objsubid IS NOT DISTINCT FROM blocking_locks.objsubid
            AND blocked_locks.pid <> blocking_locks.pid
        JOIN pg_catalog.pg_stat_activity blocked_activity
            ON blocked_activity.pid = blocked_locks.pid
        JOIN pg_catalog.pg_stat_activity blocking_activity
            ON blocking_activity.pid = blocking_locks.pid
        WHERE NOT blocked_locks.granted
        ORDER BY duracao_lock_seg DESC
        LIMIT 20
    """)


def collect_table_sizes(conn: psycopg2.extensions.connection, top_n: int = 20) -> list[dict]:
    """Tamanho das tabelas em disco (top N)."""
    return fetch_rows(conn, """
        SELECT
            relname AS tabela,
            pg_size_pretty(pg_total_relation_size(relid)) AS tamanho_total,
            pg_size_pretty(pg_relation_size(relid)) AS tamanho_dados,
            pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS tamanho_indices,
            n_live_tup AS tuplas_vivas,
            n_dead_tup AS tuplas_mortas,
            CASE
                WHEN n_live_tup > 0
                THEN ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup, 0), 1)
                ELSE 0
            END AS pct_tuplas_mortas,
            ROUND(100.0 * COALESCE(n_tup_ins, 0) / NULLIF(n_tup_ins + n_tup_upd + n_tup_del, 0), 1) AS pct_ins,
            ROUND(100.0 * COALESCE(n_tup_upd, 0) / NULLIF(n_tup_ins + n_tup_upd + n_tup_del, 0), 1) AS pct_upd,
            ROUND(100.0 * COALESCE(n_tup_del, 0) / NULLIF(n_tup_ins + n_tup_upd + n_tup_del, 0), 1) AS pct_del,
            COALESCE(n_tup_ins, 0) + COALESCE(n_tup_upd, 0) + COALESCE(n_tup_del, 0) AS operacoes_totais,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        ORDER BY pg_total_relation_size(relid) DESC
        LIMIT %(limit)s
    """, {"limit": top_n})


def collect_idle_in_transaction(conn: psycopg2.extensions.connection) -> list[dict]:
    """Conexoes ociosas em transacao (potencialmente problematicas)."""
    return fetch_rows(conn, """
        SELECT
            pid,
            usename AS usuario,
            application_name AS app,
            client_addr AS ip_cliente,
            EXTRACT(epoch FROM (NOW() - state_change))::int AS segundos_idle,
            EXTRACT(epoch FROM (NOW() - xact_start))::int AS segundos_em_transacao,
            LEFT(query, 500) AS ultima_query
        FROM pg_stat_activity
        WHERE state IN ('idle in transaction', 'idle in transaction (aborted)')
          AND pid <> pg_backend_pid()
        ORDER BY state_change ASC
    """)


def collect_replication_status(conn: psycopg2.extensions.connection) -> list[dict]:
    """Status de replicacao (se aplicavel)."""
    try:
        return fetch_rows(conn, """
            SELECT
                application_name AS nome_app,
                client_addr AS ip_replica,
                state AS estado,
                sync_state AS estado_sync,
                EXTRACT(epoch FROM (NOW() - pg_last_xact_replay_timestamp()))::int AS replay_lag_seg,
                pg_wal_lsn_diff(pg_current_wal_lsn(), sent_lsn) AS sent_lag_bytes,
                pg_wal_lsn_diff(pg_current_wal_lsn(), write_lsn) AS write_lag_bytes,
                pg_wal_lsn_diff(pg_current_wal_lsn(), flush_lsn) AS flush_lag_bytes,
                pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replay_lag_bytes
            FROM pg_stat_replication
        """)
    except Exception:
        return []


# ─── Formatacao de saida ─────────────────────────────────────────────────────

def format_text_report(data: dict) -> str:
    """Formata os dados coletados como relatorio em texto puro."""
    lines: list[str] = []
    sep = "=" * 78

    lines.append(sep)
    lines.append(f"  RELATORIO DE MONITORAMENTO — PostgreSQL (Coleta Premiada)")
    lines.append(f"  Gerado em: {data['collected_at']}")
    lines.append(sep)

    # ── Resumo do banco ──
    lines.append("\n── RESUMO POR BANCO (pg_stat_database)")
    for db in data.get("databases", []):
        cache_hit_pct = (
            round(100.0 * db["blocos_hit_cache"] / (db["blocos_hit_cache"] + db["blocos_lidos_disco"]), 1)
            if (db["blocos_hit_cache"] + db["blocos_lidos_disco"]) > 0
            else 0
        )
        lines.append(f"\n  Banco: {db['datname']}")
        lines.append(f"    Conexoes ativas: {db['conexoes_ativas']}")
        lines.append(f"    Transacoes: {db['transacoes_commit']} commit / {db['transacoes_rollback']} rollback")
        lines.append(f"    Cache hit ratio: {cache_hit_pct}%")
        lines.append(f"    Deadlocks: {db['deadlocks']}")
        lines.append(f"    Arquivos temporarios: {db['arquivos_temp']} ({db['bytes_temp']} bytes)")

    # ── Conexoes ──
    lines.append(f"\n── CONEXOES ATIVAS (pg_stat_activity) — {len(data.get('connections', []))} encontradas")
    for conn_row in data.get("connections", []):
        lines.append(
            f"  PID {conn_row['pid']:>6} | {conn_row['usuario']:<15} | {conn_row['estado']:<25} "
            f"| query={conn_row['duracao_query_seg']}s "
            f"| xact={conn_row['duracao_transacao_seg']}s "
            f"| wait={conn_row['evento_espera'] or '-'}"
        )

    # ── Idle in transaction ──
    idle_list = data.get("idle_in_transaction", [])
    if idle_list:
        lines.append(f"\n── ALERTA: CONEXOES IDLE IN TRANSACTION — {len(idle_list)} encontradas")
        for idle in idle_list:
            lines.append(
                f"  PID {idle['pid']:>6} | {idle['usuario']:<15} "
                f"| idle={idle['segundos_idle']}s "
                f"| xact={idle['segundos_em_transacao']}s "
                f"| query: {idle['ultima_query'][:120]}"
            )

    # ── Locks bloqueantes ──
    locks_list = data.get("locks", [])
    if locks_list:
        lines.append(f"\n── ALERTA: LOCKS BLOQUEANTES — {len(locks_list)} encontrados")
        for lock in locks_list:
            lines.append(
                f"  Bloqueado PID {lock['pid_bloqueado']} ({lock['usuario_bloqueado']}) "
                f"← Bloqueador PID {lock['pid_bloqueador']} ({lock['usuario_bloqueador']}) "
                f"| modo={lock['modo_lock']} | tipo={lock['tipo_lock']} "
                f"| {lock['duracao_lock_seg']}s | {lock['relacao'] or '-'}"
            )

    # ── Top queries ──
    lines.append(f"\n── TOP QUERIES POR TEMPO MEDIO (pg_stat_statements)")
    for i, q in enumerate(data.get("top_queries", []), 1):
        lines.append(f"\n  #{i} | calls={q['calls']} | media={q['tempo_medio_ms']}ms | total={q['tempo_total_ms']}ms")
        lines.append(f"       cache={q['taxa_cache_pct']}% | rows={q['rows']}")
        lines.append(f"       {q['query_truncada'][:200]}")

    # ── Tamanhos de tabela ──
    lines.append(f"\n── TOP TABELAS POR TAMANHO (pg_stat_user_tables)")
    for t in data.get("table_sizes", []):
        dead_warn = " ⚠ MUITAS TUPAS MORTAS" if t["pct_tuplas_mortas"] > 20 else ""
        lines.append(
            f"  {t['tabela']:<40} {t['tamanho_total']:>10} "
            f"| vivas={t['tuplas_vivas']} mortas={t['tuplas_mortas']} ({t['pct_tuplas_mortas']}%)"
            f"{dead_warn}"
        )
        if t["last_autovacuum"]:
            lines.append(f"    ultimo autovacuum: {t['last_autovacuum']} | autoanalyze: {t['last_autoanalyze']}")

    # ── Replicacao ──
    replication = data.get("replication", [])
    if replication:
        lines.append(f"\n── STATUS REPLICACAO (pg_stat_replication)")
        for r in replication:
            lines.append(
                f"  {r['nome_app']} ({r['ip_replica']}) | estado={r['estado']} "
                f"| sync={r['estado_sync']} | replay_lag={r['replay_lag_seg']}s"
            )

    lines.append(f"\n{sep}")
    lines.append("  FIM DO RELATORIO")
    lines.append(sep)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Relatorio de monitoramento PostgreSQL (pg_stat_statements + pg_stat_activity)",
    )
    parser.add_argument("--json", action="store_true", help="Saida em JSON")
    parser.add_argument("--output", "-o", type=str, help="Arquivo de saida (stdout se omitido)")
    parser.add_argument("--slow-ms", type=float, default=1.0, help="Threshold de queries lentas em ms (default: 1.0)")
    parser.add_argument("--top-n", type=int, default=15, help="Top N queries (default: 15)")
    args = parser.parse_args()

    try:
        conn = connect()
    except psycopg2.Error as e:
        print(f"ERRO: Falha ao conectar ao PostgreSQL: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        with conn:
            data: dict[str, Any] = {
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "databases": collect_database_stats(conn),
                "connections": collect_connections(conn),
                "idle_in_transaction": collect_idle_in_transaction(conn),
                "locks": collect_locks(conn),
                "top_queries": collect_top_queries(conn, top_n=args.top_n, min_mean_ms=args.slow_ms),
                "table_sizes": collect_table_sizes(conn),
                "replication": collect_replication_status(conn),
            }
    except psycopg2.Error as e:
        print(f"ERRO: Falha ao coletar metricas: {e}", file=sys.stderr)
        sys.exit(3)

    if args.json:
        output = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    else:
        output = format_text_report(data)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Relatorio salvo em: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
