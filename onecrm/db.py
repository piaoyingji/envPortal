from __future__ import annotations

import csv
import json
import re
import shutil
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .crypto import decrypt_text, encrypt_text
from .settings import BASE_DIR, DATABASE_URL


SECRET_FIELDS = {"login_password", "db_password", "password"}
VPN_TAG = "VPN"
VPN_REQUEST_TAG = "申请必要"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn


def init_db() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                create table if not exists organizations (
                    id uuid primary key,
                    code text not null unique,
                    name text not null,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                );
                create table if not exists environments (
                    id uuid primary key,
                    organization_id uuid not null references organizations(id) on delete cascade,
                    title text not null,
                    url text not null default '',
                    login_id text not null default '',
                    login_password text not null default '',
                    db_type text not null default '',
                    db_version text not null default '',
                    db_host text not null default '',
                    db_port integer,
                    db_name text not null default '',
                    db_user text not null default '',
                    db_password text not null default '',
                    vpn_required boolean not null default false,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                );
                create table if not exists tags (
                    id uuid primary key,
                    name text not null unique,
                    source text not null default 'manual',
                    created_at timestamptz not null default now()
                );
                create table if not exists environment_tags (
                    environment_id uuid not null references environments(id) on delete cascade,
                    tag_id uuid not null references tags(id) on delete cascade,
                    primary key(environment_id, tag_id)
                );
                create table if not exists remote_connections (
                    id uuid primary key,
                    organization_id uuid references organizations(id) on delete cascade,
                    environment_id uuid references environments(id) on delete set null,
                    scope text not null default 'private',
                    name text not null default '',
                    type text not null default 'RDP',
                    host text not null default '',
                    port integer,
                    username text not null default '',
                    password text not null default '',
                    note text not null default '',
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                );
                create table if not exists remote_connection_masters (
                    id uuid primary key,
                    scope text not null default 'shared',
                    name text not null default '',
                    type text not null default 'RDP',
                    host text not null default '',
                    port integer,
                    username text not null default '',
                    password text not null default '',
                    note text not null default '',
                    auto_match boolean not null default true,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                );
                create table if not exists environment_remote_master_links (
                    environment_id uuid not null references environments(id) on delete cascade,
                    master_id uuid not null references remote_connection_masters(id) on delete cascade,
                    created_at timestamptz not null default now(),
                    primary key(environment_id, master_id)
                );
                create table if not exists app_servers (
                    id uuid primary key,
                    environment_id uuid not null references environments(id) on delete cascade,
                    type text not null default '',
                    name text not null default '',
                    host text not null default '',
                    port integer,
                    os text not null default '',
                    note text not null default '',
                    details jsonb not null default '[]'::jsonb,
                    order_index integer not null default 0,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                );
                create table if not exists vpn_guides (
                    id uuid primary key,
                    organization_id uuid not null references organizations(id) on delete cascade,
                    name text not null default 'VPN',
                    raw_text text not null default '',
                    source_raw_text text not null default '',
                    manual_raw_text text not null default '',
                    analysis_raw_text text not null default '',
                    workflow jsonb not null default '[]'::jsonb,
                    derived_tags jsonb not null default '[]'::jsonb,
                    workflow_status text not null default 'ready',
                    workflow_source text not null default 'rule',
                    workflow_error text not null default '',
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                );
                create table if not exists audit_logs (
                    id uuid primary key,
                    actor text not null default 'admin',
                    action text not null,
                    target_type text not null,
                    target_id uuid,
                    payload jsonb not null default '{}'::jsonb,
                    created_at timestamptz not null default now()
                );
                create table if not exists users (
                    id uuid primary key,
                    username text not null unique,
                    role text not null default 'Users',
                    email text not null default '',
                    display_name text not null default '',
                    avatar_object_key text not null default '',
                    password_hash text not null,
                    password_changed_at timestamptz,
                    disabled boolean not null default false,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                );
                create table if not exists user_sessions (
                    id uuid primary key,
                    user_id uuid not null references users(id) on delete cascade,
                    token_hash text not null unique,
                    expires_at timestamptz not null,
                    created_at timestamptz not null default now(),
                    last_seen_at timestamptz not null default now()
                );
                create table if not exists password_reset_tokens (
                    id uuid primary key,
                    user_id uuid not null references users(id) on delete cascade,
                    token_hash text not null unique,
                    expires_at timestamptz not null,
                    used_at timestamptz,
                    created_at timestamptz not null default now()
                );
                create table if not exists files (
                    id uuid primary key,
                    object_key text not null,
                    filename text not null,
                    size_bytes bigint not null default 0,
                    content_type text not null default '',
                    category text not null default '',
                    created_at timestamptz not null default now()
                );
                create table if not exists file_objects (
                    id uuid primary key,
                    sha256 text not null unique,
                    object_key text not null unique,
                    filename text not null,
                    size_bytes bigint not null default 0,
                    content_type text not null default '',
                    category text not null default '',
                    created_at timestamptz not null default now()
                );
                create table if not exists vpn_guide_files (
                    id uuid primary key,
                    guide_id uuid not null references vpn_guides(id) on delete cascade,
                    file_object_id uuid not null references file_objects(id) on delete restrict,
                    original_filename text not null default '',
                    relative_path text not null default '',
                    client_modified_at timestamptz,
                    uploaded_at timestamptz not null default now(),
                    source_role text not null default 'unknown',
                    date_hints jsonb not null default '[]'::jsonb,
                    effective_from timestamptz,
                    effective_to timestamptz,
                    created_at timestamptz not null default now(),
                    unique(guide_id, file_object_id)
                );
                create table if not exists vpn_import_jobs (
                    id uuid primary key,
                    organization_id uuid not null references organizations(id) on delete cascade,
                    guide_id uuid not null references vpn_guides(id) on delete cascade,
                    status text not null default 'queued',
                    progress integer not null default 0,
                    error text not null default '',
                    raw_text text not null default '',
                    fragments jsonb not null default '[]'::jsonb,
                    warnings jsonb not null default '[]'::jsonb,
                    file_ids jsonb not null default '[]'::jsonb,
                    mode text not null default 'rebuild',
                    source_file_ids jsonb not null default '[]'::jsonb,
                    source_meta jsonb not null default '[]'::jsonb,
                    precedence_summary text not null default '',
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                );
                create table if not exists migrations (
                    name text primary key,
                    applied_at timestamptz not null default now()
                );
                """
            )
            cur.execute("alter table vpn_guides drop constraint if exists vpn_guides_organization_id_key")
            cur.execute("alter table vpn_guides add column if not exists name text not null default 'VPN'")
            cur.execute("alter table vpn_guides add column if not exists workflow_status text not null default 'ready'")
            cur.execute("alter table vpn_guides add column if not exists workflow_source text not null default 'rule'")
            cur.execute("alter table vpn_guides add column if not exists workflow_error text not null default ''")
            cur.execute("alter table vpn_guides add column if not exists derived_tags jsonb not null default '[]'::jsonb")
            cur.execute("alter table vpn_guides add column if not exists source_raw_text text not null default ''")
            cur.execute("alter table vpn_guides add column if not exists manual_raw_text text not null default ''")
            cur.execute("alter table vpn_guides add column if not exists analysis_raw_text text not null default ''")
            cur.execute("alter table vpn_guide_files add column if not exists relative_path text not null default ''")
            cur.execute("alter table vpn_guide_files add column if not exists client_modified_at timestamptz")
            cur.execute("alter table vpn_guide_files add column if not exists uploaded_at timestamptz not null default now()")
            cur.execute("alter table vpn_guide_files add column if not exists source_role text not null default 'unknown'")
            cur.execute("alter table vpn_guide_files add column if not exists date_hints jsonb not null default '[]'::jsonb")
            cur.execute("alter table vpn_guide_files add column if not exists effective_from timestamptz")
            cur.execute("alter table vpn_guide_files add column if not exists effective_to timestamptz")
            cur.execute("alter table vpn_import_jobs add column if not exists mode text not null default 'rebuild'")
            cur.execute("alter table vpn_import_jobs add column if not exists source_file_ids jsonb not null default '[]'::jsonb")
            cur.execute("alter table vpn_import_jobs add column if not exists source_meta jsonb not null default '[]'::jsonb")
            cur.execute("alter table vpn_import_jobs add column if not exists precedence_summary text not null default ''")
            cur.execute("alter table environments add column if not exists vpn_required boolean not null default false")
            cur.execute("alter table environments add column if not exists vpn_guide_id uuid references vpn_guides(id) on delete set null")
            cur.execute("alter table remote_connections add column if not exists scope text not null default 'private'")
            cur.execute("alter table remote_connections add column if not exists name text not null default ''")
            cur.execute("alter table remote_connections add column if not exists note text not null default ''")
            cur.execute("alter table app_servers add column if not exists os text not null default ''")
            cur.execute("alter table app_servers add column if not exists note text not null default ''")
            cur.execute("alter table app_servers add column if not exists details jsonb not null default '[]'::jsonb")
            cur.execute("alter table app_servers add column if not exists order_index integer not null default 0")
            cur.execute("alter table app_servers alter column type set default ''")
            cur.execute("alter table users add column if not exists avatar_object_key text not null default ''")
            cur.execute("alter table users add column if not exists disabled boolean not null default false")
            cur.execute("create index if not exists idx_user_sessions_token_hash on user_sessions(token_hash)")
            cur.execute("create index if not exists idx_password_reset_tokens_token_hash on password_reset_tokens(token_hash)")
        conn.commit()
    from .auth import ensure_admin_user
    ensure_admin_user()
    migrate_legacy_files()
    refresh_vpn_derived_tags()


def table_count(table: str) -> int:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"select count(*) as count from {table}")
            row = cur.fetchone()
            return int(row["count"] if row else 0)


def refresh_vpn_derived_tags() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select id, raw_text, analysis_raw_text, workflow, derived_tags from vpn_guides")
            guides = [dict(row) for row in cur.fetchall()]
            for guide in guides:
                tags = derive_vpn_tags(guide.get("workflow") if isinstance(guide.get("workflow"), list) else [], str(guide.get("analysis_raw_text") or guide.get("raw_text") or ""))
                current = guide.get("derived_tags") if isinstance(guide.get("derived_tags"), list) else []
                if tags != current:
                    cur.execute("update vpn_guides set derived_tags=%s where id=%s", (Jsonb(tags), guide["id"]))
                cur.execute("select id from environments where vpn_required=true and vpn_guide_id=%s", (guide["id"],))
                for env in cur.fetchall():
                    sync_vpn_request_tag(cur, env["id"], tags)
        conn.commit()


def parse_db_target(value: str) -> dict[str, Any]:
    text = (value or "").strip()
    match = re.match(r"^(?P<host>[^:/\s]+):(?P<port>\d+)[/:](?P<db>.+)$", text)
    if not match:
        return {"host": "", "port": None, "name": text}
    return {"host": match.group("host"), "port": int(match.group("port")), "name": match.group("db")}


def legacy_tag_key(row: dict[str, str]) -> str:
    return "||".join([
        row.get("組織コード", ""),
        row.get("組織名", ""),
        row.get("構築環境名", ""),
        row.get("URL", ""),
        row.get("ログインID", ""),
    ])


def backup_legacy_file(path: Path) -> None:
    if not path.exists():
        return
    backup_dir = BASE_DIR / ".tmp" / "migration-backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"{path.name}.{datetime.now().strftime('%Y%m%d%H%M%S')}.bak"
    if not target.exists():
        shutil.copy2(path, target)


def migrate_legacy_files() -> None:
    if table_count("organizations") > 0 or table_count("environments") > 0:
        return
    data_path = BASE_DIR / "data.csv"
    if not data_path.exists():
        return
    backup_legacy_file(data_path)
    backup_legacy_file(BASE_DIR / "rdp.csv")
    backup_legacy_file(BASE_DIR / "tags.json")

    tag_map: dict[str, list[str]] = {}
    tags_path = BASE_DIR / "tags.json"
    if tags_path.exists():
        try:
            tag_map = json.loads(tags_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            tag_map = {}

    with data_path.open("r", encoding="utf-8-sig", newline="") as fh, connect() as conn:
        reader = csv.DictReader(fh)
        org_ids: dict[str, uuid.UUID] = {}
        env_ids_by_org_name: dict[str, uuid.UUID] = {}
        with conn.cursor() as cur:
            for row in reader:
                code = row.get("組織コード", "").strip() or "0000"
                name = row.get("組織名", "").strip() or code
                if code not in org_ids:
                    org_id = uuid.uuid4()
                    org_ids[code] = org_id
                    cur.execute(
                        "insert into organizations(id, code, name) values(%s,%s,%s) on conflict(code) do update set name=excluded.name returning id",
                        (org_id, code, name),
                    )
                    saved = cur.fetchone()
                    if saved:
                        org_ids[code] = saved["id"]
                db_target = parse_db_target(row.get("DB名", ""))
                env_id = uuid.uuid4()
                cur.execute(
                    """
                    insert into environments(
                        id, organization_id, title, url, login_id, login_password,
                        db_type, db_version, db_host, db_port, db_name, db_user, db_password
                    ) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        env_id,
                        org_ids[code],
                        row.get("構築環境名", ""),
                        row.get("URL", ""),
                        row.get("ログインID", ""),
                        encrypt_text(row.get("ログインパスワード", "")),
                        row.get("DBタイプ", ""),
                        row.get("DBバージョン", ""),
                        db_target["host"],
                        db_target["port"],
                        db_target["name"],
                        row.get("DBユーザー名", ""),
                        encrypt_text(row.get("DBパスワード", "")),
                    ),
                )
                env_ids_by_org_name[name] = env_id
                manual_tags = tag_map.get(legacy_tag_key(row), [])
                auto_tags = [row.get("DBタイプ", ""), f"{row.get('DBタイプ', '')} {row.get('DBバージョン', '')}".strip()]
                upsert_environment_tags(cur, env_id, [tag for tag in manual_tags + auto_tags if tag], "migration")
        conn.commit()

    migrate_legacy_remote_connections()


def migrate_legacy_remote_connections() -> None:
    path = BASE_DIR / "rdp.csv"
    if not path.exists():
        return
    with path.open("r", encoding="utf-8-sig", newline="") as fh, connect() as conn:
        reader = csv.DictReader(fh)
        with conn.cursor() as cur:
            for row in reader:
                org_name = row.get("組織名", "")
                cur.execute("select id from organizations where name=%s limit 1", (org_name,))
                found = cur.fetchone()
                target = row.get("接続先(IP:Port)", "")
                host, port = parse_host_port(target, 3389 if row.get("接続タイプ", "RDP").upper() == "RDP" else 22)
                env_id = None
                org_id = found["id"] if found else None
                if not org_id and host:
                    cur.execute(
                        """
                        select e.id as environment_id, e.organization_id
                        from environments e
                        where e.url like %s or e.db_host = %s
                        order by e.created_at
                        limit 1
                        """,
                        (f"%{host}%", host),
                    )
                    matched_env = cur.fetchone()
                    if matched_env:
                        env_id = matched_env["environment_id"]
                        org_id = matched_env["organization_id"]
                cur.execute(
                    """
                    insert into remote_connections(id, organization_id, environment_id, type, host, port, username, password)
                    values(%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        uuid.uuid4(),
                        org_id,
                        env_id,
                        row.get("接続タイプ", "RDP") or "RDP",
                        host,
                        port,
                        row.get("RDPユーザー名", ""),
                        encrypt_text(row.get("RDPパスワード", "")),
                    ),
                )
        conn.commit()


def parse_host_port(target: str, default_port: int) -> tuple[str, int]:
    text = (target or "").strip()
    if ":" in text:
        host, port = text.rsplit(":", 1)
        try:
            return host, int(port)
        except ValueError:
            return text, default_port
    return text, default_port


def remote_default_port(remote_type: str) -> int:
    text = (remote_type or "RDP").strip().upper()
    if text in ("SSH",):
        return 22
    return 3389


def normalize_remote_row(row: dict[str, Any], source: str = "private") -> dict[str, Any]:
    remote = decrypt_row(dict(row))
    remote_type = remote.get("type") or "RDP"
    port = remote.get("port") or remote_default_port(remote_type)
    return {
        "id": remote.get("id"),
        "masterId": remote.get("master_id") or remote.get("masterId"),
        "organization_id": remote.get("organization_id"),
        "environment_id": remote.get("environment_id"),
        "scope": remote.get("scope") or ("shared" if source in ("shared", "autoShared") else "private"),
        "source": source,
        "name": remote.get("name") or "",
        "type": remote_type,
        "host": remote.get("host") or "",
        "port": port,
        "username": remote.get("username") or "",
        "password": remote.get("password") or "",
        "note": remote.get("note") or "",
        "autoMatch": bool(remote.get("auto_match", True)),
    }


def normalize_remote_input(value: dict[str, Any]) -> dict[str, Any]:
    remote_type = str(value.get("type") or "RDP").strip() or "RDP"
    port_value = value.get("port")
    try:
        port = int(port_value) if port_value not in (None, "") else remote_default_port(remote_type)
    except (TypeError, ValueError):
        port = remote_default_port(remote_type)
    scope = str(value.get("scope") or "private").strip()
    if scope not in ("private", "shared"):
        scope = "private"
    return {
        "id": str(value.get("id") or "").strip(),
        "masterId": str(value.get("masterId") or value.get("master_id") or "").strip(),
        "scope": scope,
        "name": str(value.get("name") or "").strip(),
        "type": remote_type,
        "host": str(value.get("host") or "").strip(),
        "port": port,
        "username": str(value.get("username") or "").strip(),
        "password": str(value.get("password") or "").strip(),
        "note": str(value.get("note") or "").strip(),
    }


def remote_key(remote: dict[str, Any]) -> tuple[str, int]:
    return ((remote.get("host") or "").strip().lower(), int(remote.get("port") or remote_default_port(remote.get("type") or "RDP")))


def upsert_environment_tags(cur: psycopg.Cursor, env_id: uuid.UUID, names: list[str], source: str = "manual") -> None:
    for name in dict.fromkeys([item.strip() for item in names if item and item.strip()]):
        tag_id = uuid.uuid4()
        cur.execute(
            "insert into tags(id, name, source) values(%s,%s,%s) on conflict(name) do update set source=coalesce(tags.source, excluded.source) returning id",
            (tag_id, name, source),
        )
        row = cur.fetchone()
        cur.execute(
            "insert into environment_tags(environment_id, tag_id) values(%s,%s) on conflict do nothing",
            (env_id, row["id"]),
        )


def remove_environment_tag(cur: psycopg.Cursor, env_id: Any, name: str) -> None:
    cur.execute(
        """
        delete from environment_tags et
        using tags t
        where et.tag_id=t.id
          and et.environment_id=%s
          and lower(t.name)=lower(%s)
        """,
        (env_id, name),
    )


def cleanup_unused_tags(cur: psycopg.Cursor) -> None:
    cur.execute(
        """
        delete from tags t
        where not exists (
            select 1 from environment_tags et where et.tag_id=t.id
        )
        """
    )


def replace_environment_user_tags(cur: psycopg.Cursor, env_id: Any, names: list[str]) -> None:
    cur.execute(
        """
        delete from environment_tags et
        using tags t
        where et.tag_id=t.id
          and et.environment_id=%s
          and coalesce(t.source, 'manual') <> 'auto'
        """,
        (env_id,),
    )
    upsert_environment_tags(cur, env_id, names, "manual")
    cleanup_unused_tags(cur)


def replace_environment_auto_tags(cur: psycopg.Cursor, env_id: Any, names: list[str]) -> None:
    cur.execute(
        """
        delete from environment_tags et
        using tags t
        where et.tag_id=t.id
          and et.environment_id=%s
          and t.source='auto'
        """,
        (env_id,),
    )
    upsert_environment_tags(cur, env_id, names, "auto")
    cleanup_unused_tags(cur)


def decrypt_row(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    for field in SECRET_FIELDS:
        if field in result:
            result[field] = decrypt_text(result[field])
    return result


def create_environment(organization_id: str, title: str, tags: list[str] | None = None) -> dict[str, Any]:
    clean_title = (title or "").strip() or "New Server"
    env_id = uuid.uuid4()
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select id from organizations where id=%s", (organization_id,))
            if not cur.fetchone():
                raise ValueError("Organization not found")
            cur.execute(
                """
                insert into environments(
                    id, organization_id, title, url, login_id, login_password,
                    db_type, db_version, db_host, db_port, db_name, db_user, db_password
                ) values(%s,%s,%s,'','',%s,'','','',null,'','',%s)
                returning *
                """,
                (env_id, organization_id, clean_title, encrypt_text(""), encrypt_text("")),
            )
            row = cur.fetchone()
            upsert_environment_tags(cur, env_id, tags or [], "manual")
        conn.commit()
    result = decrypt_row(dict(row))
    result["tags"] = [{"name": tag.strip(), "source": "manual"} for tag in tags or [] if tag and tag.strip()]
    result["appServers"] = []
    result["remoteConnections"] = []
    return result


def delete_environment(environment_id: str) -> dict[str, Any]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select id, organization_id, title from environments where id=%s", (environment_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Environment not found")
            cur.execute("delete from app_servers where environment_id=%s", (environment_id,))
            app_server_count = cur.rowcount
            cur.execute("delete from remote_connections where environment_id=%s", (environment_id,))
            remote_count = cur.rowcount
            cur.execute("delete from environment_tags where environment_id=%s", (environment_id,))
            tag_count = cur.rowcount
            cur.execute("delete from environments where id=%s", (environment_id,))
            env_count = cur.rowcount
            cleanup_unused_tags(cur)
        conn.commit()
    result = dict(row)
    result["deleted"] = {
        "environments": env_count,
        "appServers": app_server_count,
        "remoteConnections": remote_count,
        "tagLinks": tag_count,
    }
    return result


def normalize_organization(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "code": row.get("code") or "",
        "name": row.get("name") or "",
        "createdAt": row.get("created_at"),
        "updatedAt": row.get("updated_at"),
    }


def create_organization(code: str, name: str) -> dict[str, Any]:
    clean_code = (code or "").strip()
    clean_name = (name or "").strip()
    if not clean_code:
        raise ValueError("Customer code is required")
    if not clean_name:
        raise ValueError("Customer name is required")

    with connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    insert into organizations(id, code, name)
                    values(%s,%s,%s)
                    returning id, code, name, created_at, updated_at
                    """,
                    (uuid.uuid4(), clean_code, clean_name),
                )
            except psycopg.errors.UniqueViolation as exc:
                raise ValueError("Customer code already exists") from exc
            row = cur.fetchone()
        conn.commit()
    return normalize_organization(dict(row))


def update_organization(organization_id: str, code: str, name: str) -> dict[str, Any]:
    clean_code = (code or "").strip()
    clean_name = (name or "").strip()
    if not clean_code:
        raise ValueError("Customer code is required")
    if not clean_name:
        raise ValueError("Customer name is required")

    with connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    update organizations
                    set code=%s, name=%s, updated_at=now()
                    where id=%s
                    returning id, code, name, created_at, updated_at
                    """,
                    (clean_code, clean_name, organization_id),
                )
            except psycopg.errors.UniqueViolation as exc:
                raise ValueError("Customer code already exists") from exc
            row = cur.fetchone()
            if not row:
                raise ValueError("Customer not found")
        conn.commit()
    return normalize_organization(dict(row))


def organizations_with_environments() -> list[dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select * from organizations order by code")
            orgs = [dict(row) for row in cur.fetchall()]
            cur.execute(
                """
                select e.*, o.code as organization_code, o.name as organization_name
                from environments e
                join organizations o on o.id=e.organization_id
                order by o.code, e.title
                """
            )
            envs = [decrypt_row(row) for row in cur.fetchall()]
            cur.execute(
                """
                select et.environment_id, t.name, t.source
                from environment_tags et join tags t on t.id=et.tag_id
                order by t.name
                """
            )
            tags_by_env: dict[Any, list[dict[str, str]]] = {}
            for tag in cur.fetchall():
                tags_by_env.setdefault(tag["environment_id"], []).append({"name": tag["name"], "source": tag["source"]})
            cur.execute("select * from remote_connections order by type, host")
            remotes = [normalize_remote_row(dict(row), "private") for row in cur.fetchall()]
            cur.execute("select * from remote_connection_masters order by type, host, port, name")
            remote_masters = [normalize_remote_row(dict(row) | {"master_id": row["id"]}, "shared") for row in cur.fetchall()]
            masters_by_id = {master["masterId"] or master["id"]: master for master in remote_masters}
            cur.execute("select environment_id, master_id from environment_remote_master_links")
            remote_master_links: dict[Any, list[dict[str, Any]]] = {}
            for row in cur.fetchall():
                master = masters_by_id.get(row["master_id"])
                if master:
                    remote_master_links.setdefault(row["environment_id"], []).append(dict(master) | {"source": "shared"})
            cur.execute("select * from app_servers order by order_index, type, name, host")
            app_servers_by_env: dict[Any, list[dict[str, Any]]] = {}
            for row in cur.fetchall():
                app_servers_by_env.setdefault(row["environment_id"], []).append(dict(row))
            cur.execute("select id, organization_id, name, raw_text, source_raw_text, manual_raw_text, analysis_raw_text, workflow, derived_tags, workflow_status, workflow_source, workflow_error, updated_at from vpn_guides order by name, updated_at")
            guides_by_org: dict[Any, list[dict[str, Any]]] = {}
            guides_by_id: dict[Any, dict[str, Any]] = {}
            for row in cur.fetchall():
                guide = normalize_vpn_guide(dict(row))
                guides_by_org.setdefault(row["organization_id"], []).append(guide)
                guides_by_id[row["id"]] = guide
            cur.execute(
                """
                select vgf.guide_id, fo.id, fo.sha256, fo.object_key, fo.filename, fo.size_bytes, fo.content_type, fo.created_at,
                       vgf.original_filename, vgf.relative_path, vgf.client_modified_at, vgf.uploaded_at,
                       vgf.source_role, vgf.date_hints, vgf.effective_from, vgf.effective_to
                from vpn_guide_files vgf
                join file_objects fo on fo.id=vgf.file_object_id
                order by vgf.created_at, fo.filename
                """
            )
            for row in cur.fetchall():
                guide = guides_by_id.get(row["guide_id"])
                if guide is not None:
                    guide.setdefault("sourceFiles", []).append(normalize_file_object(dict(row)))

    attach_orphan_remote_connections(envs, remotes)
    envs_by_org: dict[Any, list[dict[str, Any]]] = {}
    for env in envs:
        env["tags"] = tags_by_env.get(env["id"], [])
        env["vpnGuide"] = guides_by_id.get(env.get("vpn_guide_id"))
        env["appServers"] = app_servers_by_env.get(env["id"], [])
        private_remotes = [
            remote for remote in remotes
            if remote.get("environment_id") == env["id"]
            or (not remote.get("environment_id") and remote.get("organization_id") == env["organization_id"])
        ]
        linked_remotes = remote_master_links.get(env["id"], [])
        auto_remotes = [
            dict(master) | {"source": "autoShared"}
            for master in remote_masters
            if master.get("autoMatch") and remote_matches_environment(master, env, app_servers_by_env.get(env["id"], []))
        ]
        env["remoteConnections"] = dedupe_remote_connections(private_remotes + linked_remotes + auto_remotes)
        envs_by_org.setdefault(env["organization_id"], []).append(env)
    for index, org in enumerate(orgs):
        normalized = normalize_organization(org)
        normalized["environments"] = envs_by_org.get(org["id"], [])
        normalized["vpnGuides"] = guides_by_org.get(org["id"], [])
        normalized["vpnGuide"] = normalized["vpnGuides"][0] if normalized["vpnGuides"] else None
        orgs[index] = normalized
    return orgs


def get_organization(organization_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select id, code, name, created_at, updated_at from organizations where id=%s", (organization_id,))
            row = cur.fetchone()
    return normalize_organization(dict(row)) if row else None


def normalize_vpn_guide(row: dict[str, Any]) -> dict[str, Any]:
    workflow = row.get("workflow") or []
    if not isinstance(workflow, list):
        workflow = []
    tags = row.get("derived_tags") or []
    if not isinstance(tags, list):
        tags = []
    return {
        "id": row.get("id"),
        "organization_id": row.get("organization_id"),
        "name": row.get("name") or "VPN",
        "rawText": row.get("analysis_raw_text") or row.get("raw_text") or "",
        "sourceRawText": row.get("source_raw_text") or "",
        "manualRawText": row.get("manual_raw_text") or "",
        "analysisRawText": row.get("analysis_raw_text") or row.get("raw_text") or "",
        "workflow": workflow,
        "tags": [str(tag) for tag in tags if str(tag).strip()],
        "workflowStatus": row.get("workflow_status") or "ready",
        "workflowSource": row.get("workflow_source") or "rule",
        "workflowError": row.get("workflow_error") or "",
        "updatedAt": row.get("updated_at"),
        "sourceFiles": row.get("sourceFiles") or [],
    }


def normalize_file_object(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "sha256": row.get("sha256") or "",
        "objectKey": row.get("object_key") or "",
        "filename": row.get("original_filename") or row.get("filename") or "",
        "storedFilename": row.get("filename") or "",
        "relativePath": row.get("relative_path") or row.get("original_filename") or row.get("filename") or "",
        "sizeBytes": row.get("size_bytes") or 0,
        "contentType": row.get("content_type") or "",
        "clientModifiedAt": row.get("client_modified_at"),
        "uploadedAt": row.get("uploaded_at") or row.get("created_at"),
        "sourceRole": row.get("source_role") or "unknown",
        "dateHints": row.get("date_hints") if isinstance(row.get("date_hints"), list) else [],
        "effectiveFrom": row.get("effective_from"),
        "effectiveTo": row.get("effective_to"),
        "createdAt": row.get("created_at"),
    }


def summarize_vpn_workflow(raw_text: str) -> list[dict[str, Any]]:
    text = (raw_text or "").strip()
    if not text:
        return []
    sections = split_analysis_sections(text)
    details = [
        {"label": title, "value": "\n".join(lines[:12])}
        for title, lines in sections.items()
        if lines
    ]
    credential_groups = extract_fallback_credential_groups(sections.get("対象サーバ", []))
    return [
        {
            "order": 1,
            "title": "AI分析要確認",
            "description": "AI分析に失敗したため、清掃済み原文から接続関連情報だけを保守的に表示しています。再分析してください。",
            "action": "note",
            "details": details[:4],
            "credentialGroups": credential_groups,
        }
    ]


def split_analysis_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {
        "事前準備/申請": [],
        "接続方式": [],
        "対象サーバ": [],
        "作業後対応": [],
    }
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        header = re.match(r"^##\s*(.+)$", line)
        if header:
            name = header.group(1).strip()
            current = name if name in sections else ""
            continue
        if current:
            sections[current].append(line)
    if any(sections.values()):
        return {key: unique_keep_order(value) for key, value in sections.items()}
    for line in [item.strip(" \t\r\n-・*") for item in text.splitlines() if item.strip()]:
        lowered = line.lower()
        if any(token in lowered for token in ["申請", "依頼", "許可", "承認", "電話", "連絡", "切替", "スマホ", "スマフォ"]):
            sections["事前準備/申請"].append(line)
        elif any(token in lowered for token in ["vpn", "azureportal", "bastion", "laplink", "リモート", "接続"]):
            sections["接続方式"].append(line)
        elif any(token in lowered for token in ["サーバ", "server", "db", "ap", "ip", "administrator", "password", "パスワード"]):
            sections["対象サーバ"].append(line)
        elif any(token in lowered for token in ["終了", "完了", "報告", "利用終了後"]):
            sections["作業後対応"].append(line)
    return {key: unique_keep_order(value) for key, value in sections.items()}


def unique_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def vpn_fallback_step(title: str, description: str, action: str, lines: list[str], credential_groups: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    details = [{"label": "情報", "value": line} for line in unique_keep_order(lines)[:20]]
    step: dict[str, Any] = {
        "order": 0,
        "title": title,
        "description": description,
        "action": action,
        "details": details,
    }
    if credential_groups:
        step["credentialGroups"] = credential_groups
    return step


def extract_fallback_credential_groups(lines: list[str]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in lines:
        parts = [part.strip() for part in re.split(r"\s*\|\s*", line) if part.strip()]
        text = " / ".join(parts) if parts else line
        lowered = text.lower()
        is_server_line = any(token in lowered for token in ["サーバ", "server", "db", "ap", "web", "ip", "アドレス", "windows", "oracle", "bastion"])
        if is_server_line:
            current = {
                "title": parts[0] if parts else text,
                "host": "",
                "address": "",
                "port": "",
                "protocol": "",
                "username": "",
                "password": "",
                "note": text,
                "details": [{"label": "原文", "value": text}],
            }
            groups.append(current)
        elif current is None:
            continue
        else:
            current.setdefault("details", []).append({"label": "原文", "value": text})
        target = current if current is not None else groups[-1]
        address_match = re.search(r"(?:(?:\d{1,3}\.){3}\d{1,3})(?::\d+)?", text)
        if address_match:
            target["address"] = address_match.group(0)
        user_match = re.search(r"(?:id|user|username|ユーザー名|ユーザ名|認証ID)\s*[:：]\s*([^|\s]+)|\b(administrator|[A-Za-z0-9_.-]+\\[A-Za-z0-9_.-]+)\b", text, flags=re.IGNORECASE)
        if user_match:
            target["username"] = next(group for group in user_match.groups() if group)
        password_match = re.search(r"(?:password|pass|pw|パスワード)\s*[:：]\s*(.+)$", text, flags=re.IGNORECASE)
        if password_match:
            target["password"] = password_match.group(1).strip()
    return groups[:20]


def vpn_step_title(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["申請", "申请", "request"]):
        return "申請"
    if any(token in lowered for token in ["メール", "mail", "验证码", "認証コード", "验证码", "otp"]):
        return "認証"
    if any(token in lowered for token in ["連絡", "联系", "電話", "phone"]):
        return "連絡"
    if any(token in lowered for token in ["forticlient", "yamaha", "windows vpn", "vpn"]):
        return "VPN接続"
    if any(token in lowered for token in ["rdp", "ssh", "リモート", "远程"]):
        return "遠隔接続"
    return "手順"


def vpn_step_action(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["メール", "mail", "template", "模板"]):
        return "mail"
    if any(token in lowered for token in ["申請", "申请", "request"]):
        return "request"
    if any(token in lowered for token in ["連絡", "联系", "電話", "phone"]):
        return "contact"
    if any(token in lowered for token in ["forticlient", "yamaha", "windows vpn", "vpn"]):
        return "connect"
    return "note"


def derive_vpn_tags(workflow: list[dict[str, Any]], raw_text: str = "") -> list[str]:
    tags: list[str] = []
    request_tokens = [
        "申請", "申请", "申込", "申し込み", "許可", "许可", "承認", "审批", "依頼",
        "request", "approval", "approve", "電話", "电话", "連絡", "联系", "call",
    ]

    def collect_step_text(step: dict[str, Any]) -> str:
        parts = [str(step.get("title") or ""), str(step.get("description") or ""), str(step.get("action") or "")]
        details = step.get("details")
        if isinstance(details, list):
            for detail in details:
                if isinstance(detail, dict):
                    parts.extend([str(detail.get("label") or ""), str(detail.get("value") or "")])
        mail = step.get("mailTemplate")
        if isinstance(mail, dict):
            parts.extend(str(mail.get(key) or "") for key in ["to", "cc", "bcc", "subject", "body"])
        return "\n".join(parts)

    for step in workflow or []:
        if not isinstance(step, dict):
            continue
        action = str(step.get("action") or "").strip().lower()
        text = collect_step_text(step)
        if action in {"request", "contact"} or any(token.lower() in text.lower() for token in request_tokens):
            tags.append(VPN_REQUEST_TAG)
            break
        if action == "mail" and any(token.lower() in text.lower() for token in request_tokens):
            tags.append(VPN_REQUEST_TAG)
            break
    if not tags and any(token.lower() in (raw_text or "").lower() for token in request_tokens):
        tags.append(VPN_REQUEST_TAG)
    return tags


def vpn_guide_tags_from_row(row: dict[str, Any] | None) -> list[str]:
    if not row:
        return []
    tags = row.get("derived_tags") or []
    if isinstance(tags, list) and tags:
        return [str(tag) for tag in tags if str(tag).strip()]
    workflow = row.get("workflow") or []
    if not isinstance(workflow, list):
        workflow = []
    return derive_vpn_tags(workflow, str(row.get("analysis_raw_text") or row.get("raw_text") or ""))


def get_vpn_guide(guide_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, organization_id, name, raw_text, source_raw_text, manual_raw_text, analysis_raw_text,
                       workflow, derived_tags, workflow_status, workflow_source, workflow_error, updated_at
                from vpn_guides
                where id=%s
                """,
                (guide_id,),
            )
            row = cur.fetchone()
    return normalize_vpn_guide(dict(row)) if row else None


def sync_vpn_request_tag(cur: psycopg.Cursor, env_id: Any, guide_tags: list[str]) -> None:
    if VPN_REQUEST_TAG in guide_tags:
        upsert_environment_tags(cur, env_id, [VPN_REQUEST_TAG], "auto")
    else:
        remove_environment_tag(cur, env_id, VPN_REQUEST_TAG)
    cleanup_unused_tags(cur)


def upsert_vpn_guide(organization_id: str, raw_text: str, name: str = "VPN", guide_id: str | None = None, workflow: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    workflow = workflow if workflow is not None else summarize_vpn_workflow(raw_text)
    derived_tags = derive_vpn_tags(workflow, raw_text)
    saved_id = guide_id or str(uuid.uuid4())
    clean_name = (name or "VPN").strip() or "VPN"
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into vpn_guides(id, organization_id, name, raw_text, analysis_raw_text, workflow, derived_tags)
                values(%s,%s,%s,%s,%s,%s,%s)
                on conflict(id) do update
                set name=excluded.name,
                    raw_text=excluded.raw_text,
                    analysis_raw_text=excluded.analysis_raw_text,
                    workflow=excluded.workflow,
                    derived_tags=excluded.derived_tags,
                    updated_at=now()
                returning id, organization_id, name, raw_text, source_raw_text, manual_raw_text, analysis_raw_text, workflow, derived_tags, workflow_status, workflow_source, workflow_error, updated_at
                """,
                (saved_id, organization_id, clean_name, raw_text, raw_text, Jsonb(workflow), Jsonb(derived_tags)),
            )
            row = cur.fetchone()
        conn.commit()
    return normalize_vpn_guide(dict(row))


def save_vpn_guide_raw(
    organization_id: str,
    raw_text: str,
    name: str | None = None,
    guide_id: str | None = None,
    status: str | None = None,
    source: str | None = None,
    source_raw_text: str | None = None,
    manual_raw_text: str | None = None,
    analysis_raw_text: str | None = None,
) -> dict[str, Any]:
    saved_id = guide_id or str(uuid.uuid4())
    should_update_name = name is not None
    clean_name = (name or "VPN").strip() or "VPN"
    analysis_text = analysis_raw_text if analysis_raw_text is not None else raw_text
    source_text = source_raw_text if source_raw_text is not None else None
    manual_text = manual_raw_text if manual_raw_text is not None else None
    status = status or ("analyzing" if analysis_text.strip() else "ready")
    source = source if source is not None else ("" if analysis_text.strip() else "none")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into vpn_guides(id, organization_id, name, raw_text, source_raw_text, manual_raw_text, analysis_raw_text, workflow, workflow_status, workflow_source, workflow_error)
                values(%s,%s,%s,%s,%s,%s,%s,'[]'::jsonb,%s,%s,'')
                on conflict(id) do update
                set name=case when %s then excluded.name else vpn_guides.name end,
                    raw_text=excluded.raw_text,
                    source_raw_text=case when %s then excluded.source_raw_text else vpn_guides.source_raw_text end,
                    manual_raw_text=case when %s then excluded.manual_raw_text else vpn_guides.manual_raw_text end,
                    analysis_raw_text=excluded.analysis_raw_text,
                    derived_tags='[]'::jsonb,
                    workflow_status=excluded.workflow_status,
                    workflow_source=excluded.workflow_source,
                    workflow_error='',
                    updated_at=now()
                returning id, organization_id, name, raw_text, source_raw_text, manual_raw_text, analysis_raw_text, workflow, derived_tags, workflow_status, workflow_source, workflow_error, updated_at
                """,
                (
                    saved_id,
                    organization_id,
                    clean_name,
                    analysis_text,
                    source_text or "",
                    manual_text or "",
                    analysis_text,
                    status,
                    source,
                    should_update_name,
                    source_raw_text is not None,
                    manual_raw_text is not None,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return normalize_vpn_guide(dict(row))


def update_vpn_guide_workflow(guide_id: str, workflow: list[dict[str, Any]], source: str, status: str = "ready", error: str = "") -> dict[str, Any] | None:
    derived_tags = derive_vpn_tags(workflow)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update vpn_guides
                set workflow=%s,
                    derived_tags=%s,
                    workflow_status=%s,
                    workflow_source=%s,
                    workflow_error=%s,
                    updated_at=now()
                    where id=%s
                returning id, organization_id, name, raw_text, source_raw_text, manual_raw_text, analysis_raw_text, workflow, derived_tags, workflow_status, workflow_source, workflow_error, updated_at
                """,
                (Jsonb(workflow), Jsonb(derived_tags), status, source, error[:2000], guide_id),
            )
            row = cur.fetchone()
            if row:
                cur.execute(
                    "select id from environments where vpn_required=true and vpn_guide_id=%s",
                    (guide_id,),
                )
                for env in cur.fetchall():
                    sync_vpn_request_tag(cur, env["id"], derived_tags)
        conn.commit()
    return normalize_vpn_guide(dict(row)) if row else None


def save_file_object(*, sha256: str, object_key: str, filename: str, size_bytes: int, content_type: str, category: str = "vpn-source") -> dict[str, Any]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into file_objects(id, sha256, object_key, filename, size_bytes, content_type, category)
                values(%s,%s,%s,%s,%s,%s,%s)
                on conflict(sha256) do update
                set filename=coalesce(nullif(file_objects.filename, ''), excluded.filename),
                    content_type=coalesce(nullif(file_objects.content_type, ''), excluded.content_type)
                returning id, sha256, object_key, filename, size_bytes, content_type, created_at
                """,
                (uuid.uuid4(), sha256, object_key, filename, size_bytes, content_type, category),
            )
            row = cur.fetchone()
        conn.commit()
    return normalize_file_object(dict(row))


def attach_file_to_vpn_guide(
    guide_id: str,
    file_object_id: str,
    original_filename: str,
    relative_path: str = "",
    client_modified_at: str | datetime | None = None,
) -> dict[str, Any]:
    parsed_client_modified_at = client_modified_at
    if isinstance(client_modified_at, str) and client_modified_at.strip():
        try:
            parsed_client_modified_at = datetime.fromisoformat(client_modified_at.replace("Z", "+00:00"))
        except ValueError:
            parsed_client_modified_at = None
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into vpn_guide_files(id, guide_id, file_object_id, original_filename, relative_path, client_modified_at, uploaded_at)
                values(%s,%s,%s,%s,%s,%s,now())
                on conflict(guide_id, file_object_id) do update
                set original_filename=excluded.original_filename,
                    relative_path=coalesce(nullif(excluded.relative_path, ''), vpn_guide_files.relative_path),
                    client_modified_at=coalesce(excluded.client_modified_at, vpn_guide_files.client_modified_at),
                    uploaded_at=now()
                returning id
                """,
                (uuid.uuid4(), guide_id, file_object_id, original_filename, relative_path or original_filename, parsed_client_modified_at),
            )
            cur.execute(
                """
                select fo.id, fo.sha256, fo.object_key, fo.filename, fo.size_bytes, fo.content_type, fo.created_at,
                       vgf.original_filename, vgf.relative_path, vgf.client_modified_at, vgf.uploaded_at,
                       vgf.source_role, vgf.date_hints, vgf.effective_from, vgf.effective_to
                from vpn_guide_files vgf
                join file_objects fo on fo.id=vgf.file_object_id
                where vgf.guide_id=%s and vgf.file_object_id=%s
                """,
                (guide_id, file_object_id),
            )
            row = cur.fetchone()
        conn.commit()
    return normalize_file_object(dict(row))


def vpn_guide_source_files(guide_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select fo.id, fo.sha256, fo.object_key, fo.filename, fo.size_bytes, fo.content_type, fo.created_at,
                       vgf.original_filename, vgf.relative_path, vgf.client_modified_at, vgf.uploaded_at,
                       vgf.source_role, vgf.date_hints, vgf.effective_from, vgf.effective_to
                from vpn_guide_files vgf
                join file_objects fo on fo.id=vgf.file_object_id
                where vgf.guide_id=%s
                order by coalesce(vgf.client_modified_at, vgf.uploaded_at, vgf.created_at) desc, vgf.relative_path, fo.filename
                """,
                (guide_id,),
            )
            return [normalize_file_object(dict(row)) for row in cur.fetchall()]


def file_objects_by_ids(file_ids: list[str]) -> list[dict[str, Any]]:
    clean_ids = [str(file_id) for file_id in file_ids if str(file_id).strip()]
    if not clean_ids:
        return []
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, sha256, object_key, filename, size_bytes, content_type, created_at
                from file_objects
                where id = any(%s::uuid[])
                order by filename
                """,
                (clean_ids,),
            )
            return [normalize_file_object(dict(row)) for row in cur.fetchall()]


def update_vpn_guide_file_metadata(guide_id: str, source_meta: list[dict[str, Any]]) -> None:
    by_id = {str(item.get("fileId") or item.get("id") or ""): item for item in source_meta if isinstance(item, dict)}
    if not by_id:
        return
    with connect() as conn:
        with conn.cursor() as cur:
            for file_id, meta in by_id.items():
                cur.execute(
                    """
                    update vpn_guide_files
                    set source_role=%s,
                        date_hints=%s,
                        effective_from=%s,
                        effective_to=%s
                    where guide_id=%s and file_object_id=%s
                    """,
                    (
                        str(meta.get("sourceRole") or "unknown")[:60],
                        Jsonb(meta.get("dateHints") if isinstance(meta.get("dateHints"), list) else []),
                        meta.get("effectiveFrom") or None,
                        meta.get("effectiveTo") or None,
                        guide_id,
                        file_id,
                    ),
                )
        conn.commit()


def create_vpn_import_job(
    organization_id: str,
    guide_id: str,
    files: list[dict[str, Any]],
    *,
    mode: str = "rebuild",
    source_meta: list[dict[str, Any]] | None = None,
    precedence_summary: str = "",
) -> dict[str, Any]:
    job_id = str(uuid.uuid4())
    file_ids = [str(file["id"]) for file in files if file.get("id")]
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into vpn_import_jobs(id, organization_id, guide_id, status, progress, file_ids, mode, source_file_ids, source_meta, precedence_summary)
                values(%s,%s,%s,'queued',0,%s,%s,%s,%s,%s)
                returning id, organization_id, guide_id, status, progress, error, raw_text, fragments, warnings, file_ids,
                          mode, source_file_ids, source_meta, precedence_summary, created_at, updated_at
                """,
                (job_id, organization_id, guide_id, Jsonb(file_ids), mode, Jsonb(file_ids), Jsonb(source_meta or []), precedence_summary),
            )
            row = cur.fetchone()
        conn.commit()
    return normalize_vpn_import_job(dict(row))


def update_vpn_import_job(
    job_id: str,
    *,
    status: str | None = None,
    progress: int | None = None,
    error: str | None = None,
    raw_text: str | None = None,
    fragments: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    source_file_ids: list[str] | None = None,
    source_meta: list[dict[str, Any]] | None = None,
    precedence_summary: str | None = None,
) -> dict[str, Any] | None:
    assignments = ["updated_at=now()"]
    values: list[Any] = []
    if status is not None:
        assignments.append("status=%s")
        values.append(status)
    if progress is not None:
        assignments.append("progress=%s")
        values.append(max(0, min(100, int(progress))))
    if error is not None:
        assignments.append("error=%s")
        values.append(error[:4000])
    if raw_text is not None:
        assignments.append("raw_text=%s")
        values.append(raw_text)
    if fragments is not None:
        assignments.append("fragments=%s")
        values.append(Jsonb(fragments))
    if warnings is not None:
        assignments.append("warnings=%s")
        values.append(Jsonb(warnings))
    if source_file_ids is not None:
        assignments.append("source_file_ids=%s")
        values.append(Jsonb(source_file_ids))
    if source_meta is not None:
        assignments.append("source_meta=%s")
        values.append(Jsonb(source_meta))
    if precedence_summary is not None:
        assignments.append("precedence_summary=%s")
        values.append(precedence_summary[:12000])
    values.append(job_id)
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                update vpn_import_jobs
                set {", ".join(assignments)}
                where id=%s
                returning id, organization_id, guide_id, status, progress, error, raw_text, fragments, warnings, file_ids,
                          mode, source_file_ids, source_meta, precedence_summary, created_at, updated_at
                """,
                values,
            )
            row = cur.fetchone()
        conn.commit()
    return normalize_vpn_import_job(dict(row)) if row else None


def get_vpn_import_job(job_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, organization_id, guide_id, status, progress, error, raw_text, fragments, warnings, file_ids,
                       mode, source_file_ids, source_meta, precedence_summary, created_at, updated_at
                from vpn_import_jobs
                where id=%s
                """,
                (job_id,),
            )
            row = cur.fetchone()
    return normalize_vpn_import_job(dict(row)) if row else None


def normalize_vpn_import_job(row: dict[str, Any]) -> dict[str, Any]:
    source_file_ids = row.get("source_file_ids") if isinstance(row.get("source_file_ids"), list) else []
    source_meta = row.get("source_meta") if isinstance(row.get("source_meta"), list) else []
    return {
        "id": row.get("id"),
        "organizationId": row.get("organization_id"),
        "guideId": row.get("guide_id"),
        "status": row.get("status") or "queued",
        "progress": int(row.get("progress") or 0),
        "error": row.get("error") or "",
        "rawText": row.get("raw_text") or "",
        "fragments": row.get("fragments") if isinstance(row.get("fragments"), list) else [],
        "warnings": row.get("warnings") if isinstance(row.get("warnings"), list) else [],
        "fileIds": row.get("file_ids") if isinstance(row.get("file_ids"), list) else [],
        "mode": row.get("mode") or "rebuild",
        "sourceFileIds": source_file_ids,
        "sourceFileCount": len(source_file_ids),
        "sourceMeta": source_meta,
        "precedenceSummary": row.get("precedence_summary") or "",
        "createdAt": row.get("created_at"),
        "updatedAt": row.get("updated_at"),
    }


def update_environment_vpn(environment_id: str, vpn_required: bool, vpn_guide_id: str | None) -> dict[str, Any]:
    guide_id = vpn_guide_id or None
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select organization_id from environments where id=%s", (environment_id,))
            env = cur.fetchone()
            if not env:
                raise ValueError("Environment not found")
            guide_tags: list[str] = []
            if guide_id:
                cur.execute("select id, raw_text, analysis_raw_text, workflow, derived_tags from vpn_guides where id=%s and organization_id=%s", (guide_id, env["organization_id"]))
                guide = cur.fetchone()
                if not guide:
                    raise ValueError("VPN guide does not belong to this organization")
                guide_tags = vpn_guide_tags_from_row(dict(guide))
            cur.execute(
                """
                update environments
                set vpn_required=%s,
                    vpn_guide_id=%s,
                    updated_at=now()
                where id=%s
                returning id, vpn_required, vpn_guide_id
                """,
                (vpn_required, guide_id if vpn_required else None, environment_id),
            )
            row = cur.fetchone()
            if vpn_required:
                upsert_environment_tags(cur, row["id"], [VPN_TAG], "auto")
                sync_vpn_request_tag(cur, row["id"], guide_tags)
            else:
                remove_environment_tag(cur, row["id"], VPN_TAG)
                remove_environment_tag(cur, row["id"], VPN_REQUEST_TAG)
            cleanup_unused_tags(cur)
        conn.commit()
    return dict(row)


def update_environment_details(environment_id: str, values: dict[str, Any]) -> dict[str, Any]:
    def clean(name: str) -> str:
        return str(values.get(name) or "").strip()

    def clean_tags() -> list[str]:
        raw_tags = values.get("tags")
        if isinstance(raw_tags, list):
            return [str(tag).strip() for tag in raw_tags if str(tag).strip()]
        if isinstance(raw_tags, str):
            return [tag.strip() for tag in re.split(r"[,，、\n]", raw_tags) if tag.strip()]
        return []

    port_value = values.get("db_port")
    try:
        db_port = int(port_value) if port_value not in (None, "") else None
    except (TypeError, ValueError):
        db_port = None

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select id, title, vpn_required, vpn_guide_id from environments where id=%s", (environment_id,))
            current = cur.fetchone()
            if not current:
                raise ValueError("Environment not found")
            title = clean("title") or current["title"]
            cur.execute(
                """
                update environments
                set title=%s,
                    url=%s,
                    login_id=%s,
                    login_password=%s,
                    db_type=%s,
                    db_version=%s,
                    db_host=%s,
                    db_port=%s,
                    db_name=%s,
                    db_user=%s,
                    db_password=%s,
                    updated_at=now()
                where id=%s
                returning *
                """,
                (
                    title,
                    clean("url"),
                    clean("login_id"),
                    encrypt_text(clean("login_password")),
                    clean("db_type"),
                    clean("db_version"),
                    clean("db_host"),
                    db_port,
                    clean("db_name"),
                    clean("db_user"),
                    encrypt_text(clean("db_password")),
                    environment_id,
                ),
            )
            row = cur.fetchone()
            if "tags" in values:
                replace_environment_user_tags(cur, row["id"], clean_tags())
            auto_tags = [clean("db_type"), f"{clean('db_type')} {clean('db_version')}".strip()]
            if current["vpn_required"]:
                auto_tags.append(VPN_TAG)
                if current["vpn_guide_id"]:
                    cur.execute("select raw_text, workflow, derived_tags from vpn_guides where id=%s", (current["vpn_guide_id"],))
                    auto_tags.extend(vpn_guide_tags_from_row(cur.fetchone()))
            replace_environment_auto_tags(cur, row["id"], [tag for tag in auto_tags if tag])
        conn.commit()
    return decrypt_row(dict(row))


def update_app_servers(environment_id: str, servers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select id from environments where id=%s", (environment_id,))
            if not cur.fetchone():
                raise ValueError("Environment not found")
            cur.execute("delete from app_servers where environment_id=%s", (environment_id,))
            saved: list[dict[str, Any]] = []
            for index, server in enumerate(servers):
                server_type = str(server.get("type") or "").strip()
                name = str(server.get("name") or "").strip()
                host = str(server.get("host") or "").strip()
                port_value = server.get("port")
                try:
                    port = int(port_value) if port_value not in (None, "") else None
                except (TypeError, ValueError):
                    port = None
                os_name = str(server.get("os") or "").strip()
                note = str(server.get("note") or "").strip()
                details = normalize_app_server_details(server.get("details"))
                if not any([server_type, name, host, port, os_name, note, details]):
                    continue
                cur.execute(
                    """
                    insert into app_servers(id, environment_id, type, name, host, port, os, note, details, order_index)
                    values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    returning id, environment_id, type, name, host, port, os, note, details, order_index
                    """,
                    (uuid.uuid4(), environment_id, server_type, name, host, port, os_name, note, Jsonb(details), index),
                )
                saved.append(dict(cur.fetchone()))
        conn.commit()
    return saved


def normalize_app_server_details(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    details: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or item.get("label") or "").strip()
        detail_value = str(item.get("value") or "").strip()
        if not key and not detail_value:
            continue
        details.append({"key": key, "value": detail_value})
    return details


def attach_orphan_remote_connections(envs: list[dict[str, Any]], remotes: list[dict[str, Any]]) -> None:
    for remote in remotes:
        if remote.get("environment_id") or remote.get("organization_id"):
            continue
        host = (remote.get("host") or "").strip()
        if not host:
            continue
        for env in envs:
            url = env.get("url") or ""
            db_host = env.get("db_host") or ""
            if host in url or host == db_host:
                remote["environment_id"] = env["id"]
                remote["organization_id"] = env["organization_id"]
                break


def remote_matches_environment(remote: dict[str, Any], env: dict[str, Any], app_servers: list[dict[str, Any]]) -> bool:
    host, port = remote_key(remote)
    if not host:
        return False
    candidates: set[tuple[str, int]] = set()
    if host in (env.get("url") or "").lower():
        candidates.add((host, port))
    db_host = (env.get("db_host") or "").strip().lower()
    if db_host:
        candidates.add((db_host, int(env.get("db_port") or port)))
    for server in app_servers:
        server_host = (server.get("host") or "").strip().lower()
        if server_host:
            candidates.add((server_host, int(server.get("port") or port)))
    return (host, port) in candidates


def dedupe_remote_connections(remotes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, int, str, str]] = set()
    result: list[dict[str, Any]] = []
    for remote in remotes:
        master_id = str(remote.get("masterId") or remote.get("master_id") or "").strip()
        host = (remote.get("host") or "").strip().lower()
        if master_id:
            key = ("master", master_id, 0, "", "")
        else:
            key = (
                "remote",
                host,
                int(remote.get("port") or remote_default_port(remote.get("type") or "RDP")),
                (remote.get("username") or "").strip().lower(),
                (remote.get("source") or "").strip(),
            )
        if not host or key in seen:
            continue
        seen.add(key)
        result.append(remote)
    return result


def list_remote_masters() -> list[dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select * from remote_connection_masters order by type, host, port, name")
            return [normalize_remote_row(dict(row) | {"master_id": row["id"]}, "shared") for row in cur.fetchall()]


def save_remote_master(values: dict[str, Any], master_id: str | None = None) -> dict[str, Any]:
    remote = normalize_remote_input(values)
    if not remote["host"]:
        raise ValueError("Remote host is required")
    with connect() as conn:
        with conn.cursor() as cur:
            if master_id:
                cur.execute(
                    """
                    update remote_connection_masters
                    set scope='shared', name=%s, type=%s, host=%s, port=%s, username=%s, password=%s, note=%s, auto_match=%s, updated_at=now()
                    where id=%s
                    returning *
                    """,
                    (
                        remote["name"], remote["type"], remote["host"], remote["port"],
                        remote["username"], encrypt_text(remote["password"]), remote["note"],
                        bool(values.get("autoMatch", True)), master_id,
                    ),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("Remote master not found")
            else:
                cur.execute(
                    """
                    insert into remote_connection_masters(id, scope, name, type, host, port, username, password, note, auto_match)
                    values(%s,'shared',%s,%s,%s,%s,%s,%s,%s,%s)
                    returning *
                    """,
                    (
                        uuid.uuid4(), remote["name"], remote["type"], remote["host"], remote["port"],
                        remote["username"], encrypt_text(remote["password"]), remote["note"],
                        bool(values.get("autoMatch", True)),
                    ),
                )
                row = cur.fetchone()
        conn.commit()
    return normalize_remote_row(dict(row) | {"master_id": row["id"]}, "shared")


def delete_remote_master(master_id: str) -> dict[str, Any]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from remote_connection_masters where id=%s returning id", (master_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Remote master not found")
        conn.commit()
    return {"ok": True, "id": master_id}


def update_environment_remote_connections(environment_id: str, remotes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("select id, organization_id from environments where id=%s", (environment_id,))
            env = cur.fetchone()
            if not env:
                raise ValueError("Environment not found")
            cur.execute("delete from remote_connections where environment_id=%s", (environment_id,))
            cur.execute("delete from environment_remote_master_links where environment_id=%s", (environment_id,))
            saved: list[dict[str, Any]] = []
            for item in remotes:
                remote = normalize_remote_input(item)
                if not any([remote["host"], remote["username"], remote["password"], remote["name"], remote["note"]]):
                    continue
                if remote["scope"] == "shared":
                    master_id = remote["masterId"]
                    if master_id:
                        cur.execute("select * from remote_connection_masters where id=%s", (master_id,))
                        master_row = cur.fetchone()
                        if not master_row:
                            continue
                    else:
                        cur.execute(
                            """
                            insert into remote_connection_masters(id, scope, name, type, host, port, username, password, note, auto_match)
                            values(%s,'shared',%s,%s,%s,%s,%s,%s,%s,true)
                            returning *
                            """,
                            (
                                uuid.uuid4(), remote["name"], remote["type"], remote["host"], remote["port"],
                                remote["username"], encrypt_text(remote["password"]), remote["note"],
                            ),
                        )
                        master_row = cur.fetchone()
                        master_id = str(master_row["id"])
                    cur.execute(
                        "insert into environment_remote_master_links(environment_id, master_id) values(%s,%s) on conflict do nothing",
                        (environment_id, master_id),
                    )
                    saved.append(normalize_remote_row(dict(master_row) | {"master_id": master_id}, "shared"))
                else:
                    cur.execute(
                        """
                        insert into remote_connections(id, organization_id, environment_id, scope, name, type, host, port, username, password, note)
                        values(%s,%s,%s,'private',%s,%s,%s,%s,%s,%s,%s)
                        returning *
                        """,
                        (
                            uuid.uuid4(), env["organization_id"], environment_id, remote["name"], remote["type"],
                            remote["host"], remote["port"], remote["username"], encrypt_text(remote["password"]), remote["note"],
                        ),
                    )
                    saved.append(normalize_remote_row(dict(cur.fetchone()), "private"))
        conn.commit()
    return saved


def all_tags() -> list[dict[str, str]]:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select distinct t.name, t.source
                from tags t
                join environment_tags et on et.tag_id=t.id
                order by t.name
                """
            )
            return [dict(row) for row in cur.fetchall()]


def audit(action: str, target_type: str, target_id: Any | None = None, payload: dict[str, Any] | None = None, actor: str = "admin") -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into audit_logs(id, actor, action, target_type, target_id, payload) values(%s,%s,%s,%s,%s,%s)",
                (uuid.uuid4(), actor, action, target_type, target_id, Jsonb(json_safe(payload or {}))),
            )
        conn.commit()


def json_safe(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    return value
