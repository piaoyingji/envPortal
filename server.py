import csv
import ctypes
from ctypes import wintypes
import hashlib
import hmac
import json
import os
import re
import signal
import shutil
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import base64
import ipaddress
import uuid
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def load_env():
    config = {}
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()
    return config


CONFIG = load_env()


def env_float(name, default):
    try:
        return float(CONFIG.get(name, str(default)) or default)
    except ValueError:
        return float(default)


def env_bool(name, default=False):
    value = str(CONFIG.get(name, "")).strip().lower()
    if not value:
        return bool(default)
    return value in {"1", "true", "yes", "on"}


PORT = int(CONFIG.get("PORT", "8080"))
BIND_ADDRESS = CONFIG.get("BIND_ADDRESS", "0.0.0.0")
AUTH_PASSWORD = CONFIG.get("AUTH_PASSWORD", "nho1234567")
WINDOWS_AUTH_HEADER = CONFIG.get("WINDOWS_AUTH_HEADER", "X-Remote-User")
WINDOWS_AUTH_WHITELIST = CONFIG.get("WINDOWS_AUTH_WHITELIST", "")
TRUSTED_AUTH_PROXY_IPS = CONFIG.get("TRUSTED_AUTH_PROXY_IPS", "")
RDP_SIGN_THUMBPRINT = CONFIG.get("RDP_SIGN_THUMBPRINT", "").replace(" ", "")
RDP_CERT_SUBJECT = CONFIG.get("RDP_CERT_SUBJECT", "CN=EnvPortal RDP Signing")
GUACAMOLE_URL = CONFIG.get("GUACAMOLE_URL", "").rstrip("/")
GUACAMOLE_PUBLIC_URL = CONFIG.get("GUACAMOLE_PUBLIC_URL", "").rstrip("/")
GUACAMOLE_USERNAME = CONFIG.get("GUACAMOLE_USERNAME", "")
GUACAMOLE_PASSWORD = CONFIG.get("GUACAMOLE_PASSWORD", "")
DOMAIN_AUTH_PROXY_URL = CONFIG.get("DOMAIN_AUTH_PROXY_URL", "").rstrip("/")
DOMAIN_AUTH_AUTO_PROBE = env_bool("DOMAIN_AUTH_AUTO_PROBE", False)
AUTH_TOKEN_SECRET = CONFIG.get("AUTH_TOKEN_SECRET", AUTH_PASSWORD)
AUTH_TOKEN_TTL_SECONDS = int(CONFIG.get("AUTH_TOKEN_TTL_SECONDS", "28800"))
GUACAMOLE_STATUS_CACHE = {"checked_at": 0, "available": False, "message": "not checked"}
GUACAMOLE_DRIVE_ROOT = BASE_DIR / "guacamole-drive"
GUACAMOLE_DRIVE_RETENTION_HOURS = env_float("GUACAMOLE_DRIVE_RETENTION_HOURS", 24)
GUACAMOLE_DRIVE_CLEANUP_INTERVAL_SECONDS = 3600
GUACAMOLE_DRIVE_LAST_CLEANUP = 0


def json_bytes(payload):
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


PORTAL_CSV_FIELDS = [
    "組織コード",
    "組織名",
    "環境グループ",
    "構築環境名",
    "URL",
    "ログインID",
    "ログインパスワード",
    "DBタイプ",
    "DBバージョン",
    "DB名",
    "DBユーザー名",
    "DBパスワード",
]
RDP_CSV_FIELDS = [
    "組織名",
    "接続タイプ",
    "RDPユーザー名",
    "RDPパスワード",
    "接続先(IP:Port)",
]
PRODUCTION_CSV_FIELDS = [
    "組織名",
    "構築環境名",
    "使用VPN",
    "VPN IP",
    "VPNユーザー名",
    "VPNパスワード",
    "踏み台IP",
    "踏み台ユーザー名",
    "踏み台パスワード",
    "AP IP",
    "APユーザー名",
    "APパスワード",
    "DB IP",
    "DBユーザー名",
    "DBパスワード",
]
SENSITIVE_STATIC_FILES = {"/data.csv", "/rdp.csv", "/production.csv", "/users.json", "/roles.json"}
REMOVED_MANAGEMENT_PAGES = {"/admin.html", "/rdp.html", "/production-admin.html"}
PORTAL_MASK_FIELDS = {"ログインパスワード", "DBパスワード"}
RDP_MASK_FIELDS = {"RDPユーザー名", "RDPパスワード"}
PRODUCTION_MASK_FIELDS = {"VPNパスワード", "踏み台パスワード", "APパスワード", "DBパスワード"}
USERS_PATH = BASE_DIR / "users.json"
ROLES_PATH = BASE_DIR / "roles.json"
DEFAULT_ROLES = {
    "admin": {
        "key": "admin",
        "label": "管理者",
        "canEdit": True,
        "canManageUsers": True,
        "filterTag": "",
        "protected": True,
    },
    "staff": {
        "key": "staff",
        "label": "一般職員",
        "canEdit": False,
        "canManageUsers": False,
        "filterTag": "",
        "protected": False,
    },
    "import_staff": {
        "key": "import_staff",
        "label": "導入職員",
        "canEdit": False,
        "canManageUsers": False,
        "filterTag": "OneHR",
        "protected": False,
    },
    "new_employee": {
        "key": "new_employee",
        "label": "新入社員",
        "canEdit": False,
        "canManageUsers": False,
        "filterTag": "社内学習",
        "protected": False,
    },
}
DEFAULT_ORG_READINGS = {
    "標準版": "ひょうじゅんばん",
    "森林整備センター": "しんりんせいびせんたー",
    "東京-受入テスト": "とうきょううけいれてすと",
}


def read_csv_records(filename, fields):
    path = BASE_DIR / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = []
        for row in csv.DictReader(handle):
            rows.append({field: row.get(field, "") for field in fields})
        return rows


def read_tags_json():
    path = BASE_DIR / "tags.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig") or "{}")
    except json.JSONDecodeError:
        return {}


def row_key(row):
    return "||".join(str(row.get(field, "") or "").strip() for field in [
        "組織コード",
        "組織名",
        "構築環境名",
        "URL",
        "ログインID",
    ])


def legacy_row_key(row):
    return "||".join(str(row.get(field, "") or "").strip() for field in [
        "組織名",
        "構築環境名",
        "URL",
        "ログインID",
    ])


def tags_for_row(row, tags_json):
    record = tags_json.get(row_key(row), tags_json.get(legacy_row_key(row), []))
    if isinstance(record, list):
        return [str(tag).strip() for tag in record if str(tag).strip()]
    if isinstance(record, dict) and isinstance(record.get("tags"), list):
        return [str(tag).strip() for tag in record["tags"] if str(tag).strip()]
    return []


def filter_tags_for_rows(tags_json, rows):
    keys = set()
    for row in rows:
        keys.add(row_key(row))
        keys.add(legacy_row_key(row))
    return {key: value for key, value in tags_json.items() if key in keys}


def normalize_role_key(value):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "").strip()).strip("_").lower()


def normalize_role_record(key, record):
    role_key = normalize_role_key(record.get("key") if isinstance(record, dict) else key)
    if not role_key:
        return None
    defaults = DEFAULT_ROLES.get(role_key, {})
    protected = bool(defaults.get("protected"))
    role = {
        "key": role_key,
        "label": str((record or {}).get("label") or defaults.get("label") or role_key),
        "canEdit": bool((record or {}).get("canEdit", defaults.get("canEdit", False))),
        "canManageUsers": bool((record or {}).get("canManageUsers", defaults.get("canManageUsers", False))),
        "filterTag": str((record or {}).get("filterTag") or defaults.get("filterTag") or "").strip(),
        "protected": protected,
    }
    if role_key == "admin":
        role["canEdit"] = True
        role["canManageUsers"] = True
        role["protected"] = True
    return role


def load_roles():
    roles = {}
    raw = {}
    if ROLES_PATH.exists():
        try:
            data = json.loads(ROLES_PATH.read_text(encoding="utf-8-sig") or "{}")
            if isinstance(data, dict):
                raw = data
        except json.JSONDecodeError:
            raw = {}
    for key, record in {**DEFAULT_ROLES, **raw}.items():
        normalized = normalize_role_record(key, record if isinstance(record, dict) else {})
        if normalized:
            roles[normalized["key"]] = normalized
    if "admin" not in roles:
        roles["admin"] = dict(DEFAULT_ROLES["admin"])
    return roles


def save_roles(roles):
    cleaned = {}
    for key, record in roles.items():
        normalized = normalize_role_record(key, record if isinstance(record, dict) else {})
        if normalized:
            cleaned[normalized["key"]] = normalized
    if "admin" not in cleaned:
        cleaned["admin"] = dict(DEFAULT_ROLES["admin"])
    cleaned["admin"]["canEdit"] = True
    cleaned["admin"]["canManageUsers"] = True
    cleaned["admin"]["protected"] = True
    ROLES_PATH.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def role_options():
    return sorted(load_roles().values(), key=lambda item: item.get("key", ""))


def role_keys():
    return set(load_roles().keys())


def role_config(role):
    roles = load_roles()
    return roles.get(role) or roles.get("staff") or DEFAULT_ROLES["staff"]


def portal_rows_for_role(rows, tags_json, role):
    tag_name = role_config(role).get("filterTag", "")
    if not tag_name:
        return rows
    return [row for row in rows if tag_name in tags_for_row(row, tags_json)]


def load_users():
    if not USERS_PATH.exists():
        return {}
    try:
        data = json.loads(USERS_PATH.read_text(encoding="utf-8-sig") or "{}")
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def save_users(users):
    USERS_PATH.write_text(json.dumps(users, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_text():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())


def base64url_encode(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def base64url_decode(value):
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def sign_auth_token(user, expires_at):
    payload = f"{normalize_windows_user(user)}.{int(expires_at)}"
    signature = hmac.new(AUTH_TOKEN_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return f"{base64url_encode(payload.encode('utf-8'))}.{base64url_encode(signature)}"


def verify_auth_token(token):
    text = str(token or "").strip()
    if "." not in text:
        return ""
    payload_part, signature_part = text.split(".", 1)
    try:
        payload = base64url_decode(payload_part).decode("utf-8")
        expected = base64url_encode(hmac.new(AUTH_TOKEN_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest())
    except Exception:
        return ""
    if not hmac.compare_digest(signature_part, expected):
        return ""
    user, _, expires_text = payload.rpartition(".")
    try:
        expires_at = int(expires_text)
    except ValueError:
        return ""
    if expires_at < int(time.time()):
        return ""
    return normalize_windows_user(user)


def auth_token_from_headers(headers):
    value = headers.get("X-EnvPortal-Auth", "")
    if value:
        return value.strip()
    authorization = headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def attach_auth_token(profile):
    if not profile.get("user"):
        return profile
    expires_at = int(time.time()) + AUTH_TOKEN_TTL_SECONDS
    profile["authToken"] = sign_auth_token(profile["user"], expires_at)
    profile["authTokenExpiresAt"] = expires_at
    return profile


def user_profile_for(user, is_initial_admin=False, client_ip="", metadata=None):
    metadata = metadata or {}
    normalized = normalize_windows_user(user)
    if not normalized:
        return {"user": "", "role": "staff", "canEdit": False, "canManageUsers": False}
    users = load_users()
    now = now_text()
    record = users.get(normalized)
    if not record:
        record = {
            "user": normalized,
            "displayName": metadata.get("displayName") or user or normalized,
            "role": "admin" if is_initial_admin else "staff",
            "firstSeen": now,
            "lastSeen": now,
            "firstIp": client_ip or "",
            "lastIp": client_ip or "",
        }
        users[normalized] = record
        save_users(users)
    else:
        record["lastSeen"] = now
        if metadata.get("displayName"):
            record["displayName"] = metadata["displayName"]
        else:
            record.setdefault("displayName", user or normalized)
        if client_ip:
            record.setdefault("firstIp", record.get("lastIp") or client_ip)
            record["lastIp"] = client_ip
        if record.get("role") not in role_keys():
            record["role"] = "staff"
        for key in ("email", "department", "title"):
            if metadata.get(key):
                record[key] = metadata[key]
        users[normalized] = record
        save_users(users)
    role = record.get("role", "staff")
    role_info = role_config(role)
    return {
        "user": normalized,
        "displayName": record.get("displayName", normalized),
        "role": role,
        "canEdit": bool(role_info.get("canEdit")),
        "canManageUsers": bool(role_info.get("canManageUsers")),
        "lastIp": record.get("lastIp", ""),
        "email": record.get("email", ""),
        "department": record.get("department", ""),
        "title": record.get("title", ""),
    }


def masked_records(rows, mask_fields):
    return [
        {key: ("" if key in mask_fields and value else value) for key, value in row.items()}
        for row in rows
    ]


def append_change_log(user, client_ip, endpoint, filename, before_text, after_text):
    logs_dir = BASE_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "user": user or "",
        "clientIp": client_ip or "",
        "endpoint": endpoint,
        "file": filename,
        "before": before_text,
        "after": after_text,
        "afterSummary": {
            "bytes": len(after_text.encode("utf-8")),
            "lines": len(after_text.splitlines()),
        },
    }
    with (logs_dir / "change_log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def append_change_summary_log(user, client_ip, endpoint, files, change_summary):
    logs_dir = BASE_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "user": user or "",
        "clientIp": client_ip or "",
        "endpoint": endpoint,
        "files": files,
        "changeSummary": change_summary if isinstance(change_summary, dict) else {},
    }
    with (logs_dir / "change_log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def parse_form(body):
    return {k: v[0] if v else "" for k, v in urllib.parse.parse_qs(body, keep_blank_values=True).items()}


def normalize_windows_user(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if "\\" in text:
        text = text.rsplit("\\", 1)[-1]
    if "@" in text:
        text = text.split("@", 1)[0]
    return text.strip().lower()


def load_windows_auth_whitelist():
    users = set()
    for value in WINDOWS_AUTH_WHITELIST.split(","):
        normalized = normalize_windows_user(value)
        if normalized:
            users.add(normalized)
    whitelist_path = BASE_DIR / "windows_auth_whitelist.txt"
    if whitelist_path.exists():
        for line in whitelist_path.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            normalized = normalize_windows_user(text)
            if normalized:
                users.add(normalized)
    return users


def parse_ip_entries(values):
    entries = []
    for value in values:
        text = str(value or "").strip()
        if not text or text.startswith("#"):
            continue
        try:
            if "/" in text:
                entries.append(ipaddress.ip_network(text, strict=False))
            else:
                entries.append(ipaddress.ip_address(text))
        except ValueError:
            continue
    return entries


def ip_matches_entries(ip_text, entries):
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return False
    for entry in entries:
        if isinstance(entry, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
            if ip in entry:
                return True
        elif ip == entry:
            return True
    return False


def trusted_auth_proxy(headers, client_address):
    raw_values = [item for item in TRUSTED_AUTH_PROXY_IPS.split(",") if item.strip()]
    trusted_path = BASE_DIR / "trusted_auth_proxies.txt"
    if trusted_path.exists():
        raw_values.extend(trusted_path.read_text(encoding="utf-8").splitlines())
    entries = parse_ip_entries(raw_values)
    if not entries:
        return True
    peer_ip = client_address[0] if client_address else ""
    return ip_matches_entries(peer_ip, entries)


def client_ip_from_request(headers, client_address):
    forwarded_for = headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    real_ip = headers.get("X-Real-IP", "")
    if real_ip:
        return real_ip.strip()
    return client_address[0] if client_address else ""


def load_org_reading_overrides():
    readings_path = BASE_DIR / "org_readings.js"
    overrides = dict(DEFAULT_ORG_READINGS)
    if not readings_path.exists():
        return overrides
    text = readings_path.read_text(encoding="utf-8")
    pairs = re.findall(r"'([^']+)'\s*:\s*'([^']*)'", text)
    overrides.update({name.strip(): reading.strip() for name, reading in pairs if name.strip()})
    return overrides


def js_string(value):
    return str(value or "").replace("\\", "\\\\").replace("'", "\\'")


def save_org_reading_overrides(overrides):
    readings_path = BASE_DIR / "org_readings.js"
    lines = ["window.ORG_READING_OVERRIDES = {"]
    for index, name in enumerate(sorted(overrides.keys(), key=lambda item: item.lower())):
        suffix = "," if index < len(overrides) - 1 else ""
        lines.append(f"    '{js_string(name)}': '{js_string(overrides[name])}'{suffix}")
    lines.append("};")
    readings_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def kana_text_to_hiragana(text):
    chars = []
    for char in str(text or ""):
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            chars.append(chr(code - 0x60))
        else:
            chars.append(char)
    return "".join(chars)


def infer_org_reading(name):
    text = str(name or "").strip()
    if not text:
        return ""
    try:
        import pykakasi
        kakasi = pykakasi.kakasi()
        converted = kakasi.convert(text)
        reading = "".join(item.get("hira") or item.get("kana") or item.get("orig") or "" for item in converted)
        reading = re.sub(r"[\s\-_・･]+", "", kana_text_to_hiragana(reading))
        if reading:
            return reading
    except Exception:
        pass
    first = normalize_kana_initial(to_hiragana_initial(text))
    if first:
        return re.sub(r"[\s\-_・･]+", "", kana_text_to_hiragana(text))
    return ""


def sync_org_readings():
    overrides = load_org_reading_overrides()
    added = {}
    unresolved = []
    for name in csv_org_names():
        if overrides.get(name):
            continue
        reading = infer_org_reading(name)
        if reading:
            overrides[name] = reading
            added[name] = reading
        else:
            unresolved.append(name)
    if added or not (BASE_DIR / "org_readings.js").exists():
        save_org_reading_overrides(overrides)
    return {"added": added, "unresolved": unresolved}


def csv_org_names():
    names = set()
    for path in BASE_DIR.glob("*.csv"):
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    name = str(row.get("組織名", "") or "").strip()
                    if name:
                        names.add(name)
        except Exception:
            continue
    return sorted(names)


def to_hiragana_initial(text):
    if not text:
        return ""
    char = str(text)[0]
    code = ord(char)
    if 0x30A1 <= code <= 0x30F6:
        return chr(code - 0x60)
    return char


def normalize_kana_initial(char):
    mapping = {
        "ぁ": "あ", "ぃ": "い", "ぅ": "う", "ぇ": "え", "ぉ": "お",
        "が": "か", "ぎ": "き", "ぐ": "く", "げ": "け", "ご": "こ",
        "ざ": "さ", "じ": "し", "ず": "す", "ぜ": "せ", "ぞ": "そ",
        "だ": "た", "ぢ": "ち", "づ": "つ", "で": "て", "ど": "と",
        "っ": "つ",
        "ば": "は", "び": "ひ", "ぶ": "ふ", "べ": "へ", "ぼ": "ほ",
        "ぱ": "は", "ぴ": "ひ", "ぷ": "ふ", "ぺ": "へ", "ぽ": "ほ",
        "ゃ": "や", "ゅ": "ゆ", "ょ": "よ",
    }
    if char in mapping:
        return mapping[char]
    if char in "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん":
        return char
    return ""


def org_reading_status():
    sync_result = sync_org_readings()
    overrides = load_org_reading_overrides()
    records = []
    missing = []
    for name in csv_org_names():
        reading = overrides.get(name, "")
        source = "manual" if reading else "name"
        group = normalize_kana_initial(to_hiragana_initial(reading or name)) or "その他"
        record = {"name": name, "reading": reading, "group": group, "source": source}
        records.append(record)
        if group == "その他" and not reading:
            missing.append(name)
    return {"records": records, "missing": missing, "synced": sync_result}


def windows_user_from_headers(headers):
    header_names = [
        WINDOWS_AUTH_HEADER,
        "X-Remote-User",
        "X-Forwarded-User",
        "Remote-User",
        "REMOTE_USER",
    ]
    for name in header_names:
        if not name:
            continue
        value = headers.get(name)
        if value:
            return value.strip()
    return ""


def request_windows_auth(headers):
    raw_user = windows_user_from_headers(headers)
    user = normalize_windows_user(raw_user)
    return user, bool(user)


def windows_user_metadata_from_headers(headers):
    def decode_header(name):
        return urllib.parse.unquote((headers.get(name) or "").strip())
    return {
        "displayName": decode_header("X-Remote-Display-Name"),
        "email": decode_header("X-Remote-Mail"),
        "department": decode_header("X-Remote-Department"),
        "title": decode_header("X-Remote-Title"),
    }


def local_windows_user_fallback(client_address):
    host = client_address[0] if client_address else ""
    if host not in ("127.0.0.1", "::1", "localhost"):
        return "", False
    user = normalize_windows_user(os.environ.get("USERNAME", ""))
    return user, bool(user and user in load_windows_auth_whitelist())


def http_post_form(url, data, timeout=8):
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    context = ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=timeout, context=context) as res:
        body = res.read().decode("utf-8", errors="replace")
        content_type = res.headers.get("Content-Type", "")
        if "application/json" in content_type or body.strip().startswith(("{", "[")):
            return json.loads(body)
        return body


def http_json_request(url, method="GET", payload=None, token="", timeout=8):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Guacamole-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    context = ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=timeout, context=context) as res:
        body = res.read().decode("utf-8", errors="replace")
        if not body.strip():
            return {}
        return json.loads(body)


def guacamole_status(ttl_seconds=10):
    if not GUACAMOLE_URL:
        return {"available": False, "message": "Guacamole is not configured."}
    now = time.time()
    if now - GUACAMOLE_STATUS_CACHE["checked_at"] < ttl_seconds:
        return {
            "available": GUACAMOLE_STATUS_CACHE["available"],
            "message": GUACAMOLE_STATUS_CACHE["message"],
        }
    try:
        if GUACAMOLE_USERNAME and GUACAMOLE_PASSWORD:
            token_response = http_post_form(
                f"{GUACAMOLE_URL}/api/tokens",
                {"username": GUACAMOLE_USERNAME, "password": GUACAMOLE_PASSWORD},
                timeout=3,
            )
            available = bool(isinstance(token_response, dict) and token_response.get("authToken"))
            message = "API token ok" if available else "Guacamole token was not returned."
        else:
            check_url = GUACAMOLE_URL + "/"
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(check_url, timeout=1.5, context=context) as response:
                available = 200 <= response.status < 500
                message = f"HTTP {response.status}"
    except Exception as exc:
        available = False
        message = str(exc)
    GUACAMOLE_STATUS_CACHE.update({
        "checked_at": now,
        "available": available,
        "message": message,
    })
    return {"available": available, "message": message}


def guacamole_token():
    if not GUACAMOLE_URL or not GUACAMOLE_USERNAME or not GUACAMOLE_PASSWORD:
        return "", "", "Guacamole credentials are not configured."
    try:
        token_response = http_post_form(
            f"{GUACAMOLE_URL}/api/tokens",
            {"username": GUACAMOLE_USERNAME, "password": GUACAMOLE_PASSWORD},
            timeout=5,
        )
        token = token_response.get("authToken", "") if isinstance(token_response, dict) else ""
        if not token:
            return "", "", "Guacamole token was not returned."
        data_source = token_response.get("dataSource", "") or "postgresql"
        return token, data_source, ""
    except Exception as exc:
        return "", "", str(exc)


def cleanup_guacamole_drive_sessions(force=False):
    global GUACAMOLE_DRIVE_LAST_CLEANUP
    if GUACAMOLE_DRIVE_RETENTION_HOURS <= 0:
        return
    now = time.time()
    if not force and now - GUACAMOLE_DRIVE_LAST_CLEANUP < GUACAMOLE_DRIVE_CLEANUP_INTERVAL_SECONDS:
        return
    GUACAMOLE_DRIVE_LAST_CLEANUP = now
    sessions_root = GUACAMOLE_DRIVE_ROOT / "sessions"
    if not sessions_root.exists():
        return
    cutoff = now - (GUACAMOLE_DRIVE_RETENTION_HOURS * 3600)
    for session_dir in sessions_root.iterdir():
        try:
            if not session_dir.is_dir():
                continue
            last_changed = session_dir.stat().st_mtime
            for path in session_dir.rglob("*"):
                last_changed = max(last_changed, path.stat().st_mtime)
            if last_changed < cutoff:
                shutil.rmtree(session_dir)
        except OSError:
            continue


def new_guacamole_drive_path():
    cleanup_guacamole_drive_sessions()
    session_id = uuid.uuid4().hex
    host_path = GUACAMOLE_DRIVE_ROOT / "sessions" / session_id
    try:
        host_path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return f"/drive/sessions/{session_id}"


def build_guacamole_uri(target, user="", password="", drive_path=""):
    target = str(target or "").strip()
    user = str(user or "").strip()
    password = str(password or "")
    authority = target
    if user:
        credential = urllib.parse.quote(user, safe="")
        if password:
            credential += ":" + urllib.parse.quote(password, safe="")
        authority = credential + "@" + target
    params = {
        "ignore-cert": "true",
        "security": "any",
        "disable-audio": "true",
        "enable-wallpaper": "false",
    }
    if drive_path:
        params.update({
            "enable-drive": "true",
            "drive-name": "EnvPortal",
            "drive-path": drive_path,
            "create-drive-path": "true",
        })
    params = urllib.parse.urlencode(params)
    return f"rdp://{authority}/?{params}"


def parse_remote_target(target, default_port=3389):
    text = str(target or "").strip()
    if not text:
        return "", str(default_port)
    if "/" in text:
        text = text.split("/", 1)[0]
    if text.startswith("[") and "]" in text:
        host = text[1:text.index("]")]
        rest = text[text.index("]") + 1:]
        port = rest[1:] if rest.startswith(":") and rest[1:] else str(default_port)
        return host, port
    if ":" in text:
        host, port = text.rsplit(":", 1)
        return host.strip(), port.strip() or str(default_port)
    return text, str(default_port)


def guacamole_client_identifier(connection_id, data_source):
    raw = f"{connection_id}\0c\0{data_source}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def create_guacamole_rdp_connection(target, user="", password="", token="", data_source="postgresql", drive_path=""):
    host, port = parse_remote_target(target)
    if not host:
        return "", "Missing RDP target"
    name = safe_filename(f"EnvPortal_{host}_{int(time.time())}", "EnvPortal_RDP")
    drive_path = drive_path or new_guacamole_drive_path()
    payload = {
        "parentIdentifier": "ROOT",
        "name": name,
        "protocol": "rdp",
        "parameters": {
            "hostname": host,
            "port": port,
            "username": user or "",
            "password": password or "",
            "security": "any",
            "ignore-cert": "true",
            "disable-copy": "false",
            "disable-paste": "false",
            "normalize-clipboard": "windows",
            "enable-drive": "true",
            "drive-name": "EnvPortal",
            "drive-path": drive_path,
            "create-drive-path": "true",
            "enable-wallpaper": "false",
            "disable-audio": "true",
            "resize-method": "display-update",
        },
        "attributes": {
            "max-connections": "",
            "max-connections-per-user": "",
            "weight": "",
            "failover-only": "",
            "guacd-hostname": "",
            "guacd-port": "",
            "guacd-encryption": "",
        },
    }
    try:
        created = http_json_request(
            f"{GUACAMOLE_URL}/api/session/data/{urllib.parse.quote(data_source)}/connections",
            method="POST",
            payload=payload,
            token=token,
        )
        identifier = created.get("identifier", "") if isinstance(created, dict) else ""
        if not identifier:
            return "", "Guacamole connection identifier was not returned."
        return identifier, ""
    except Exception as exc:
        return "", str(exc)


def public_guacamole_url(request_host=""):
    source_url = GUACAMOLE_PUBLIC_URL or GUACAMOLE_URL
    if not source_url:
        return ""
    parsed = urllib.parse.urlparse(source_url)
    if parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        return source_url
    host_header = str(request_host or "").split(":")[0].strip()
    if not host_header or host_header in ("localhost", "127.0.0.1", "::1"):
        return source_url
    netloc = host_header
    if parsed.port:
        netloc += f":{parsed.port}"
    return urllib.parse.urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))


def guacamole_quickconnect(target, user="", password="", public_url=""):
    drive_path = new_guacamole_drive_path()
    quickconnect_uri = build_guacamole_uri(target, user, password, drive_path)
    display_url = public_url or GUACAMOLE_URL
    auto_login_url = "/guacamole_auto_login.jsp" if GUACAMOLE_USERNAME and GUACAMOLE_PASSWORD else display_url
    status = guacamole_status(ttl_seconds=0)
    if not GUACAMOLE_URL:
        return {
            "ok": False,
            "mode": "disabled",
            "guacamoleUrl": "",
            "quickconnectUri": quickconnect_uri,
            "message": "Guacamole is not configured.",
        }
    if not status["available"]:
        return {
            "ok": False,
            "mode": "unavailable",
            "guacamoleUrl": display_url,
            "quickconnectUri": quickconnect_uri,
            "message": "Guacamole is not reachable: " + status["message"],
        }

    fallback = {
        "ok": True,
        "mode": "manual",
        "guacamoleUrl": auto_login_url,
        "quickconnectUri": quickconnect_uri,
        "message": "Open Guacamole and paste the QuickConnect URI.",
    }
    if not GUACAMOLE_USERNAME or not GUACAMOLE_PASSWORD:
        return fallback

    token, data_source, token_error = guacamole_token()
    if not token:
        print("Guacamole token failed:", token_error or "token was not returned")
        return {**fallback, "message": token_error or "Guacamole token was not returned."}

    quickconnect_error = ""
    try:
        created = http_post_form(
            f"{GUACAMOLE_URL}/api/session/ext/quickconnect/create?token={urllib.parse.quote(token)}",
            {"uri": quickconnect_uri},
        )
        identifier = created.get("identifier", "") if isinstance(created, dict) else ""
        if identifier:
            return {
                "ok": True,
                "mode": "direct",
                "url": f"{display_url}/#/client/{urllib.parse.quote(identifier)}?token={urllib.parse.quote(token)}",
                "guacamoleUrl": display_url,
                "quickconnectUri": quickconnect_uri,
                "message": "",
            }
        quickconnect_error = "Guacamole QuickConnect did not return an identifier."
    except Exception as exc:
        quickconnect_error = str(exc)
        print("Guacamole QuickConnect failed, trying REST connection creation:", quickconnect_error)

    created_id, create_error = create_guacamole_rdp_connection(target, user, password, token, data_source, drive_path)
    if not created_id:
        print("Guacamole REST connection creation failed:", create_error)
        return {**fallback, "message": create_error or quickconnect_error or "Guacamole connection could not be created."}
    print(f"Guacamole temporary RDP connection created: {created_id}")
    client_id = guacamole_client_identifier(created_id, data_source)
    return {
        "ok": True,
        "mode": "direct",
        "url": f"{display_url}/#/client/{urllib.parse.quote(client_id)}?token={urllib.parse.quote(token)}",
        "guacamoleUrl": display_url,
        "quickconnectUri": quickconnect_uri,
        "message": "",
    }


def safe_filename(value, fallback="remote"):
    text = re.sub(r"[^\w\-.]+", "_", str(value or "").strip(), flags=re.UNICODE).strip("._")
    return text or fallback


def dpapi_encrypt_hex(text):
    if os.name != "nt" or not text:
        return ""

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    data = text.encode("utf-16-le")
    input_buffer = ctypes.create_string_buffer(data)
    input_blob = DATA_BLOB(len(data), ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_byte)))
    output_blob = DATA_BLOB()

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(output_blob),
    )
    if not ok:
        return ""
    try:
        encrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return encrypted.hex().upper()
    finally:
        kernel32.LocalFree(output_blob.pbData)


def build_rdp_file(target, user="", password=""):
    target = str(target or "").strip()
    user = str(user or "").strip()
    password = str(password or "")
    encrypted_password = dpapi_encrypt_hex(password)
    lines = [
        "screen mode id:i:2",
        "use multimon:i:0",
        "desktopwidth:i:1280",
        "desktopheight:i:768",
        "session bpp:i:32",
        "winposstr:s:0,1,0,0,1280,768",
        "compression:i:1",
        "keyboardhook:i:2",
        "audiocapturemode:i:0",
        "videoplaybackmode:i:1",
        "connection type:i:7",
        "networkautodetect:i:1",
        "bandwidthautodetect:i:1",
        "displayconnectionbar:i:1",
        "enableworkspacereconnect:i:0",
        "disable wallpaper:i:0",
        "allow font smoothing:i:1",
        "allow desktop composition:i:1",
        "disable full window drag:i:0",
        "disable menu anims:i:0",
        "disable themes:i:0",
        "disable cursor setting:i:0",
        "bitmapcachepersistenable:i:1",
        f"full address:s:{target}",
        "audiomode:i:0",
        "redirectprinters:i:0",
        "redirectcomports:i:0",
        "redirectsmartcards:i:0",
        "redirectclipboard:i:0",
        "redirectwebauthn:i:0",
        "redirectposdevices:i:0",
        "drivestoredirect:s:",
        "autoreconnection enabled:i:1",
        "authentication level:i:2",
        "prompt for credentials:i:0" if encrypted_password else "prompt for credentials:i:1",
        "negotiate security layer:i:1",
        "remoteapplicationmode:i:0",
        "alternate shell:s:",
        "shell working directory:s:",
        "gatewayhostname:s:",
        "gatewayusagemethod:i:4",
        "gatewaycredentialssource:i:4",
        "gatewayprofileusagemethod:i:0",
        "promptcredentialonce:i:0",
        "use redirection server name:i:0",
        "enablecredsspsupport:i:1",
    ]
    if user:
        lines.append(f"username:s:{user}")
    if encrypted_password:
        lines.append(f"password 51:b:{encrypted_password}")
    return b"\xff\xfe" + ("\r\n".join(lines) + "\r\n").encode("utf-16-le")


def rdp_credential_targets(target):
    text = str(target or "").strip()
    if not text:
        return []
    host = text.split("/")[0].strip()
    host_without_port = host.split(":")[0].strip()
    values = []
    for item in (host, host_without_port):
        if item and item not in values:
            values.append(item)
    targets = []
    for item in values:
        targets.append(f"TERMSRV/{item}")
        targets.append(item)
    return targets


def save_rdp_credential(target, user, password):
    if os.name != "nt" or not target or not user or not password:
        return
    for credential_target in rdp_credential_targets(target):
        subprocess.run(
            ["cmdkey", f"/delete:{credential_target}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        result = subprocess.run(
            [
                "cmdkey",
                f"/add:{credential_target}",
                f"/user:{user}",
                f"/pass:{password}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            print("cmdkey failed:", (result.stdout + result.stderr).strip())


def launch_mstsc(target):
    if os.name != "nt" or not target:
        return False, "mstsc launch is only supported on Windows."
    try:
        subprocess.Popen(
            ["mstsc.exe", f"/v:{target}"],
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        return True, ""
    except Exception as exc:
        return False, str(exc)


def powershell_text(script):
    temp_dir = BASE_DIR / ".tmp"
    temp_dir.mkdir(exist_ok=True)
    script_path = temp_dir / f"envportal_ps_{int(time.time() * 1000)}.ps1"
    try:
        script_path.write_text("Import-Module Microsoft.PowerShell.Security\n" + script, encoding="utf-8-sig")
        env = os.environ.copy()
        env["PSModulePath"] = ";".join([
            str(Path.home() / "Documents" / "WindowsPowerShell" / "Modules"),
            str(Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "WindowsPowerShell" / "Modules"),
            str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "system32" / "WindowsPowerShell" / "v1.0" / "Modules"),
        ])
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
            capture_output=True,
            text=True,
            timeout=20,
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "").strip())
        return (result.stdout or "").strip()
    finally:
        try:
            script_path.unlink(missing_ok=True)
        except Exception:
            pass


def get_or_create_rdp_cert_thumbprint():
    if os.name != "nt":
        return ""
    if RDP_SIGN_THUMBPRINT:
        return RDP_SIGN_THUMBPRINT

    escaped_subject = RDP_CERT_SUBJECT.replace("'", "''")
    script = f"""
$subject = '{escaped_subject}'
$cert = Get-ChildItem Cert:\\CurrentUser\\My |
  Where-Object {{ $_.Subject -eq $subject -and $_.HasPrivateKey }} |
  Sort-Object NotAfter -Descending |
  Select-Object -First 1
if (-not $cert) {{
  $cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject $subject `
    -CertStoreLocation Cert:\\CurrentUser\\My `
    -KeyExportPolicy Exportable `
    -KeyUsage DigitalSignature `
    -NotAfter (Get-Date).AddYears(5)
}}
$cert.Thumbprint
"""
    try:
        return powershell_text(script).replace(" ", "")
    except Exception as exc:
        print("RDP certificate creation failed:", exc)
        return ""


def export_rdp_cert():
    thumbprint = get_or_create_rdp_cert_thumbprint()
    if not thumbprint:
        return None
    temp_dir = BASE_DIR / ".tmp"
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"EnvPortal_RDP_Signing_{int(time.time() * 1000)}.cer"
    escaped_path = str(temp_path).replace("'", "''")
    escaped_thumb = thumbprint.replace("'", "''")
    script = f"""
$cert = Get-Item Cert:\\CurrentUser\\My\\{escaped_thumb}
Export-Certificate -Cert $cert -FilePath '{escaped_path}' -Force | Out-Null
"""
    try:
        powershell_text(script)
        return temp_path.read_bytes()
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


def sign_rdp_payload(payload, filename_base):
    thumbprint = get_or_create_rdp_cert_thumbprint()
    if os.name != "nt" or not thumbprint:
        return payload
    temp_dir = BASE_DIR / ".tmp"
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"{safe_filename(filename_base)}_{int(time.time() * 1000)}.rdp"
    try:
        temp_path.write_bytes(payload)
        result = subprocess.run(
            ["rdpsign", "/sha256", thumbprint, str(temp_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            print("RDP signing failed:", (result.stdout + result.stderr).strip())
            return payload
        return temp_path.read_bytes()
    except Exception as exc:
        print("RDP signing failed:", exc)
        return payload
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass


def detect_db_target(db_name):
    text = (db_name or "").strip()
    match = re.match(r"^(?P<host>[^:/\s]+):(?P<port>\d+)[/:](?P<db>.+)$", text)
    if not match:
        return None
    port = int(match.group("port"))
    db_type = "Oracle" if port == 1521 else "PostgreSQL" if port == 5432 else ""
    return {
        "host": match.group("host"),
        "port": port,
        "database": match.group("db"),
        "type": db_type,
        "raw": text,
    }


def probe_database(db_name, user, password):
    target = detect_db_target(db_name)
    if not target or not target["type"]:
        return {"ok": False, "type": "", "version": "", "message": "Unsupported connection string"}
    if not user or not password:
        return {"ok": False, "type": target["type"], "version": "", "message": "Credentials required for version probe"}

    if target["type"] == "Oracle":
        try:
            import oracledb
        except ImportError:
            return {"ok": False, "type": "Oracle", "version": "", "message": "Python package missing: oracledb"}
        try:
            try:
                dsn = oracledb.makedsn(target["host"], target["port"], service_name=target["database"])
                conn = oracledb.connect(user=user, password=password, dsn=dsn)
            except Exception as service_exc:
                try:
                    dsn = oracledb.makedsn(target["host"], target["port"], sid=target["database"])
                    conn = oracledb.connect(user=user, password=password, dsn=dsn)
                except Exception:
                    raise service_exc
            with conn:
                banner = f"Oracle Database {getattr(conn, 'version', '')}".strip()
                try:
                    with conn.cursor() as cur:
                        cur.execute("select banner from v$version where banner like 'Oracle Database%'")
                        row = cur.fetchone()
                        if row and row[0]:
                            banner = row[0]
                except Exception:
                    pass
            version = extract_major_version(banner, "Oracle")
            return {"ok": True, "type": "Oracle", "version": version, "message": banner}
        except Exception as exc:
            return {"ok": False, "type": "Oracle", "version": "", "message": friendly_db_error(str(exc))}

    if target["type"] == "PostgreSQL":
        try:
            import psycopg
        except ImportError:
            return {"ok": False, "type": "PostgreSQL", "version": "", "message": "Python package missing: psycopg"}
        try:
            conninfo = (
                f"host={target['host']} port={target['port']} dbname={target['database']} "
                f"user={user} password={password} connect_timeout=3"
            )
            with psycopg.connect(conninfo) as conn:
                banner = conn.info.parameter_status("server_version") or ""
                if not banner:
                    with conn.cursor() as cur:
                        cur.execute("select version()")
                        banner = cur.fetchone()[0]
            version = extract_major_version(banner, "PostgreSQL")
            return {"ok": True, "type": "PostgreSQL", "version": version, "message": banner}
        except Exception as exc:
            return {"ok": False, "type": "PostgreSQL", "version": "", "message": friendly_db_error(str(exc))}

    return {"ok": False, "type": target["type"], "version": "", "message": "Unsupported database type"}


def extract_major_version(text, db_type=""):
    value = text or ""
    if db_type == "Oracle":
        match = re.search(r"Oracle(?:\s+Database)?\s+(\d+)", value, re.IGNORECASE)
        if match:
            return match.group(1)
    if db_type == "PostgreSQL":
        match = re.search(r"PostgreSQL\s+(\d+)", value, re.IGNORECASE)
        if match:
            return match.group(1)
    match = re.search(r"\b(\d{2})(?:c|g|\.\d+)*\b", value, re.IGNORECASE)
    return match.group(1) if match else ""


def friendly_db_error(message):
    text = str(message or "").strip()
    if "DPY-4027" in text:
        return "Oracle driver could not parse the connection target. Use host, port, and service/SID fields; no Oracle config directory should be required."
    if "ORA-01017" in text:
        return "Oracle login failed: invalid username or password."
    if "ORA-12154" in text:
        return "Oracle connection name could not be resolved."
    if "ORA-12514" in text:
        return "Oracle listener does not know the requested service name."
    if "ORA-12505" in text:
        return "Oracle listener does not know the requested SID."
    if "ORA-12170" in text or "timed out" in text.lower():
        return "Database connection timed out."
    return text


def local_lan_ips():
    values = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and ip not in values:
                values.append(ip)
    except Exception:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
        if ip and not ip.startswith("127.") and ip not in values:
            values.append(ip)
        probe.close()
    except Exception:
        pass
    return values


def add_platform_score(scores, name, points, evidence):
    if not name:
        return
    current = scores.setdefault(name, {"score": 0, "evidence": []})
    current["score"] += points
    if evidence and evidence not in current["evidence"]:
        current["evidence"].append(evidence)


def detect_server_stack(server, powered_by, content_type="", url=""):
    text = f"{server or ''} {powered_by or ''} {content_type or ''}".lower()
    parsed = urllib.parse.urlparse(url or "")
    port = parsed.port

    if re.search(r"apache-coyote|tomcat", text):
        return "Tomcat"
    if re.search(r"weblogic", text):
        return "WebLogic"
    if re.search(r"websphere", text):
        return "WebSphere"
    if re.search(r"wildfly|jboss", text):
        return "WildFly / JBoss"
    if re.search(r"jetty", text):
        return "Jetty"
    if re.search(r"iis|asp\.net", text):
        return "IIS / ASP.NET"
    if re.search(r"nginx", text):
        return "Nginx"
    if re.search(r"\bapache\b", text):
        return "Apache HTTP Server"
    if re.search(r"servlet|jsp|java", text):
        return "Java App Server"
    if re.search(r"php", text):
        return "PHP Web Server"
    if port in (8080, 8081, 8888, 9080, 9443):
        return "Java App Server"
    return ""


def guess_os(server, powered_by, content_type="", ttl_guess=""):
    text = f"{server or ''} {powered_by or ''} {content_type or ''}".lower()
    scores = {}

    if re.search(r"iis|asp\.net|windows", text):
        add_platform_score(scores, "Windows", 80, "HTTP header")
    if re.search(r"ubuntu|debian|centos|red hat|rhel|linux", text):
        add_platform_score(scores, "Linux / Unix", 70, "HTTP header")

    if ttl_guess and ttl_guess != "Unknown":
        ttl_name = "Windows" if "Windows" in ttl_guess else "Linux / Unix" if "Linux" in ttl_guess or "Unix" in ttl_guess else ""
        add_platform_score(scores, ttl_name, 20, f"TTL {ttl_guess}")

    if not scores:
        return {"name": "Unknown", "evidence": [], "confidence": "low"}

    best_name, best = max(scores.items(), key=lambda item: item[1]["score"])
    score = best["score"]
    confidence = "high" if score >= 80 else "medium" if score >= 45 else "low"
    return {"name": best_name, "evidence": best["evidence"][:3], "confidence": confidence}


def ping_ttl(host):
    try:
        if os.name == "nt":
            cmd = ["ping", "-n", "1", "-w", "1200", host]
        else:
            cmd = ["ping", "-c", "1", "-W", "1", host]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        text = result.stdout + result.stderr
        match = re.search(r"ttl[=\s](\d+)", text, re.IGNORECASE)
        if not match:
            return "", "Unknown"
        ttl = int(match.group(1))
        if 96 < ttl <= 128:
            return ttl, "Windows-like"
        if 32 < ttl <= 64:
            return ttl, "Linux/Unix-like"
        if ttl > 128:
            return ttl, "Network device / Unix-like"
        return ttl, "Unknown"
    except Exception:
        return "", "Unknown"


def env_check(url):
    started = time.perf_counter()
    context = ssl._create_unverified_context()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=1.2, context=context) as res:
            elapsed = int((time.perf_counter() - started) * 1000)
            server = res.headers.get("Server", "")
            powered_by = res.headers.get("X-Powered-By", "")
            content_type = res.headers.get("Content-Type", "")
            host = urllib.parse.urlparse(url).hostname or ""
            ttl, ttl_guess = ping_ttl(host)
            platform_guess = guess_os(server, powered_by, content_type, ttl_guess)
            server_stack = detect_server_stack(server, powered_by, content_type, url)
            return {
                "status": res.status,
                "elapsedMs": elapsed,
                "server": server,
                "poweredBy": powered_by,
                "contentType": content_type,
                "finalUrl": res.url,
                "platform": platform_guess["name"],
                "platformConfidence": platform_guess["confidence"],
                "platformEvidence": platform_guess["evidence"],
                "serverStack": server_stack,
                "ttl": ttl,
                "ttlGuess": ttl_guess,
            }
    except Exception:
        return {
            "status": "ERROR",
            "elapsedMs": int((time.perf_counter() - started) * 1000),
            "server": "",
            "poweredBy": "",
            "contentType": "",
            "finalUrl": "",
            "platform": "Unknown",
            "platformConfidence": "low",
            "platformEvidence": [],
            "serverStack": "",
            "ttl": "",
            "ttlGuess": "Unknown",
        }


class EnvPortalHandler(SimpleHTTPRequestHandler):
    server_version = "EnvPortalPython/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def send_bytes(self, payload, content_type="text/plain; charset=utf-8", status=200):
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def send_download(self, payload, filename, content_type="application/x-rdp"):
        quoted = urllib.parse.quote(filename)
        try:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quoted}")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def send_redirect(self, url):
        payload = b""
        try:
            self.send_response(302)
            self.send_header("Location", url)
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Content-Length", "0")
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def request_auth(self):
        token_user = verify_auth_token(auth_token_from_headers(self.headers))
        if token_user:
            return token_user, False, "token"
        if windows_user_from_headers(self.headers) and trusted_auth_proxy(self.headers, self.client_address):
            user, trusted = request_windows_auth(self.headers)
            return user, trusted, "windows"
        user, trusted = local_windows_user_fallback(self.client_address)
        return user, trusted, "local" if user else ""

    def request_profile(self):
        user, initial_admin, auth_source = self.request_auth()
        client_ip = client_ip_from_request(self.headers, self.client_address)
        profile = user_profile_for(user, initial_admin, client_ip, windows_user_metadata_from_headers(self.headers))
        if auth_source == "windows":
            attach_auth_token(profile)
        profile["ip"] = client_ip
        profile["ok"] = bool(profile.get("user"))
        return profile

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        path = urllib.parse.urlparse(self.path).path

        if path == "/auth.jsp":
            profile = self.request_profile()
            self.send_bytes(b"OK" if profile.get("canEdit") else b"NG")
            return

        if path == "/auth_windows.jsp":
            self.send_bytes(json_bytes(self.request_profile()), "application/json; charset=utf-8")
            return

        protected_post_paths = {
            "/db_probe.jsp",
            "/rdp_file.jsp",
            "/rdp_connect.jsp",
            "/guacamole_connect.jsp",
            "/update_csv.jsp",
            "/update_rdp.jsp",
            "/update_tags.jsp",
            "/update_production.jsp",
            "/update_users.jsp",
            "/update_roles.jsp",
            "/update_portal_bundle.jsp",
        }
        if path in protected_post_paths:
            profile = self.request_profile()
            if not profile.get("canEdit"):
                self.send_bytes(b"Forbidden", status=403)
                return
        if path in {"/update_users.jsp", "/update_roles.jsp"}:
            profile = self.request_profile()
            if not profile.get("canManageUsers"):
                self.send_bytes(b"Forbidden", status=403)
                return

        if path == "/db_probe.jsp":
            form = parse_form(body)
            result = probe_database(form.get("dbName", ""), form.get("dbUser", ""), form.get("dbPwd", ""))
            self.send_bytes(json_bytes(result), "application/json; charset=utf-8")
            return

        if path == "/rdp_file.jsp":
            form = parse_form(body)
            target = form.get("target", "")
            if not target.strip():
                self.send_bytes(b"Missing RDP target", status=400)
                return
            org = safe_filename(form.get("org", ""))
            env = safe_filename(form.get("env", ""))
            filename_base = safe_filename("_".join(part for part in [org, env] if part), "remote")
            save_rdp_credential(target, form.get("user", ""), form.get("password", ""))
            payload = build_rdp_file(target, form.get("user", ""), form.get("password", ""))
            payload = sign_rdp_payload(payload, filename_base)
            self.send_download(payload, f"{filename_base}.rdp")
            return

        if path == "/rdp_connect.jsp":
            form = parse_form(body)
            target = form.get("target", "")
            if not target.strip():
                self.send_bytes(json_bytes({"ok": False, "message": "Missing RDP target"}), "application/json; charset=utf-8", status=400)
                return
            save_rdp_credential(target, form.get("user", ""), form.get("password", ""))
            ok, message = launch_mstsc(target)
            self.send_bytes(json_bytes({"ok": ok, "message": message}), "application/json; charset=utf-8", status=200 if ok else 500)
            return

        if path == "/guacamole_connect.jsp":
            form = parse_form(body)
            target = form.get("target", "")
            if not target.strip():
                self.send_bytes(json_bytes({"ok": False, "message": "Missing RDP target"}), "application/json; charset=utf-8", status=400)
                return
            result = guacamole_quickconnect(
                target,
                form.get("user", ""),
                form.get("password", ""),
                public_guacamole_url(self.headers.get("Host", "")),
            )
            self.send_bytes(json_bytes(result), "application/json; charset=utf-8", status=200 if result.get("ok") else 500)
            return

        if path == "/update_portal_bundle.jsp":
            try:
                payload = json.loads(body or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("payload must be object")
                data_csv = str(payload.get("dataCsv", ""))
                rdp_csv = str(payload.get("rdpCsv", ""))
                tags_json_text = payload.get("tagsJson", "{}")
                if not isinstance(tags_json_text, str):
                    tags_json_text = json.dumps(tags_json_text, ensure_ascii=False, indent=2)
                json.loads(tags_json_text or "{}")
                change_summary = payload.get("changeSummary", {})
                if not isinstance(change_summary, dict):
                    change_summary = {}
            except Exception as exc:
                self.send_bytes(f"Invalid portal bundle: {exc}".encode("utf-8"), status=400)
                return

            files = {
                "data.csv": data_csv,
                "rdp.csv": rdp_csv,
                "tags.json": tags_json_text,
            }
            for filename, content in files.items():
                (BASE_DIR / filename).write_text(content, encoding="utf-8-sig", newline="")
            profile = self.request_profile()
            append_change_summary_log(
                profile.get("user", ""),
                client_ip_from_request(self.headers, self.client_address),
                path,
                list(files.keys()),
                change_summary,
            )
            self.send_bytes(b"success")
            return

        update_map = {
            "/update_csv.jsp": "data.csv",
            "/update_rdp.jsp": "rdp.csv",
            "/update_tags.jsp": "tags.json",
            "/update_production.jsp": "production.csv",
            "/update_users.jsp": "users.json",
            "/update_roles.jsp": "roles.json",
        }
        if path in update_map:
            filename = update_map[path]
            target_path = BASE_DIR / filename
            before_text = target_path.read_text(encoding="utf-8-sig") if target_path.exists() else ""
            profile = self.request_profile()
            append_change_log(profile.get("user", ""), client_ip_from_request(self.headers, self.client_address), path, filename, before_text, body)
            if path == "/update_users.jsp":
                try:
                    incoming = json.loads(body or "{}")
                    if not isinstance(incoming, dict):
                        raise ValueError("users payload must be object")
                    cleaned = {}
                    current = load_users()
                    for key, record in incoming.items():
                        normalized = normalize_windows_user(key)
                        if not normalized or not isinstance(record, dict):
                            continue
                        role = record.get("role", "staff")
                        if role not in role_keys():
                            role = "staff"
                        old = current.get(normalized, {})
                        cleaned[normalized] = {
                            "user": normalized,
                            "displayName": str(record.get("displayName") or old.get("displayName") or normalized),
                            "role": role,
                            "firstSeen": str(record.get("firstSeen") or old.get("firstSeen") or now_text()),
                            "lastSeen": str(record.get("lastSeen") or old.get("lastSeen") or now_text()),
                            "firstIp": str(record.get("firstIp") or old.get("firstIp") or ""),
                            "lastIp": str(record.get("lastIp") or old.get("lastIp") or ""),
                            "email": str(record.get("email") or old.get("email") or ""),
                            "department": str(record.get("department") or old.get("department") or ""),
                            "title": str(record.get("title") or old.get("title") or ""),
                        }
                    body = json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n"
                except Exception as exc:
                    self.send_bytes(f"Invalid users.json: {exc}".encode("utf-8"), status=400)
                    return
            if path == "/update_roles.jsp":
                try:
                    incoming = json.loads(body or "{}")
                    if not isinstance(incoming, dict):
                        raise ValueError("roles payload must be object")
                    save_roles(incoming)
                    body = ROLES_PATH.read_text(encoding="utf-8")
                except Exception as exc:
                    self.send_bytes(f"Invalid roles.json: {exc}".encode("utf-8"), status=400)
                    return
            target_path.write_text(body, encoding="utf-8-sig", newline="")
            self.send_bytes(b"success")
            return

        self.send_bytes(b"Not Found", status=404)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in REMOVED_MANAGEMENT_PAGES:
            self.send_bytes(b"Not Found", status=404)
            return

        protected_pages = set()
        if path in protected_pages:
            profile = self.request_profile()
            if not profile.get("canEdit"):
                self.send_bytes(b"Forbidden", status=403)
                return

        if path in SENSITIVE_STATIC_FILES:
            profile = self.request_profile()
            if not profile.get("canEdit"):
                self.send_bytes(b"Forbidden", status=403)
                return

        if path == "/auth_windows.jsp":
            self.send_bytes(json_bytes(self.request_profile()), "application/json; charset=utf-8")
            return

        if path == "/portal_data.jsp":
            profile = self.request_profile()
            role = profile.get("role", "staff")
            data_rows = read_csv_records("data.csv", PORTAL_CSV_FIELDS)
            rdp_rows = read_csv_records("rdp.csv", RDP_CSV_FIELDS)
            tags_json = read_tags_json()
            data_rows = portal_rows_for_role(data_rows, tags_json, role)
            visible_orgs = {str(row.get("組織名", "") or "").strip() for row in data_rows}
            if not profile.get("canEdit"):
                data_rows = masked_records(data_rows, PORTAL_MASK_FIELDS)
                rdp_rows = [row for row in rdp_rows if str(row.get("組織名", "") or "").strip() in visible_orgs]
                rdp_rows = masked_records(rdp_rows, RDP_MASK_FIELDS)
            self.send_bytes(json_bytes({
                "ok": profile.get("ok", False),
                "user": profile.get("user", ""),
                "displayName": profile.get("displayName", ""),
                "email": profile.get("email", ""),
                "department": profile.get("department", ""),
                "title": profile.get("title", ""),
                "role": role,
                "canEdit": profile.get("canEdit", False),
                "canManageUsers": profile.get("canManageUsers", False),
                "fields": PORTAL_CSV_FIELDS,
                "rdpFields": RDP_CSV_FIELDS,
                "data": data_rows,
                "rdp": rdp_rows,
                "tags": filter_tags_for_rows(tags_json, data_rows),
            }), "application/json; charset=utf-8")
            return

        if path == "/production_data.jsp":
            profile = self.request_profile()
            rows = read_csv_records("production.csv", PRODUCTION_CSV_FIELDS)
            if not profile.get("canEdit"):
                rows = []
            self.send_bytes(json_bytes({
                "ok": profile.get("ok", False),
                "user": profile.get("user", ""),
                "displayName": profile.get("displayName", ""),
                "email": profile.get("email", ""),
                "department": profile.get("department", ""),
                "title": profile.get("title", ""),
                "role": profile.get("role", "staff"),
                "canEdit": profile.get("canEdit", False),
                "canManageUsers": profile.get("canManageUsers", False),
                "fields": PRODUCTION_CSV_FIELDS,
                "data": rows,
            }), "application/json; charset=utf-8")
            return

        if path == "/users_data.jsp":
            profile = self.request_profile()
            if not profile.get("canManageUsers"):
                self.send_bytes(b"Forbidden", status=403)
                return
            self.send_bytes(json_bytes({
                "ok": True,
                "user": profile.get("user", ""),
                "displayName": profile.get("displayName", ""),
                "email": profile.get("email", ""),
                "department": profile.get("department", ""),
                "title": profile.get("title", ""),
                "role": profile.get("role", "staff"),
                "canEdit": profile.get("canEdit", False),
                "canManageUsers": profile.get("canManageUsers", False),
                "roles": role_options(),
                "users": load_users(),
            }), "application/json; charset=utf-8")
            return

        if path == "/roles_data.jsp":
            profile = self.request_profile()
            if not profile.get("canManageUsers"):
                self.send_bytes(b"Forbidden", status=403)
                return
            self.send_bytes(json_bytes({
                "ok": True,
                "user": profile.get("user", ""),
                "displayName": profile.get("displayName", ""),
                "email": profile.get("email", ""),
                "department": profile.get("department", ""),
                "title": profile.get("title", ""),
                "role": profile.get("role", "staff"),
                "canEdit": profile.get("canEdit", False),
                "canManageUsers": profile.get("canManageUsers", False),
                "roles": role_options(),
                "users": load_users(),
            }), "application/json; charset=utf-8")
            return

        if path == "/client_info.jsp":
            self.send_bytes(json_bytes({
                "clientIp": client_ip_from_request(self.headers, self.client_address),
            }), "application/json; charset=utf-8")
            return

        if path == "/org_readings_status.jsp":
            self.send_bytes(json_bytes(org_reading_status()), "application/json; charset=utf-8")
            return

        if path == "/ping.jsp":
            url = query.get("url", [""])[0]
            result = env_check(url)
            self.send_bytes(str(result["status"]).encode("utf-8"))
            return

        if path == "/env_check.jsp":
            url = query.get("url", [""])[0]
            self.send_bytes(json_bytes(env_check(url)), "application/json; charset=utf-8")
            return

        if path == "/portal_config.jsp":
            guac_status = guacamole_status()
            self.send_bytes(json_bytes({
                "clientIp": client_ip_from_request(self.headers, self.client_address),
                "domainAuthProxyUrl": DOMAIN_AUTH_PROXY_URL,
                "domainAuthAutoProbe": DOMAIN_AUTH_AUTO_PROBE,
                "guacamoleEnabled": bool(GUACAMOLE_URL),
                "guacamoleAvailable": guac_status["available"],
                "guacamoleStatus": guac_status["message"],
                "guacamoleUrl": "/guacamole_auto_login.jsp" if GUACAMOLE_USERNAME and GUACAMOLE_PASSWORD else public_guacamole_url(self.headers.get("Host", "")),
                "guacamoleAutoLogin": bool(GUACAMOLE_URL and GUACAMOLE_USERNAME and GUACAMOLE_PASSWORD),
            }), "application/json; charset=utf-8")
            return

        if path == "/guacamole_auto_login.jsp":
            public_url = public_guacamole_url(self.headers.get("Host", ""))
            if not public_url:
                self.send_bytes(b"Guacamole is not configured.", status=404)
                return
            if not GUACAMOLE_USERNAME or not GUACAMOLE_PASSWORD:
                self.send_redirect(public_url)
                return
            query = urllib.parse.urlencode({
                "username": GUACAMOLE_USERNAME,
                "password": GUACAMOLE_PASSWORD,
            })
            redirect_url = public_url + "/#/" + "?" + query
            self.send_redirect(redirect_url)
            return

        if path == "/rdp_signing_cert.cer":
            payload = export_rdp_cert()
            if not payload:
                self.send_bytes(b"RDP signing certificate is not available on this platform.", status=404)
                return
            self.send_download(payload, "EnvPortal_RDP_Signing.cer", "application/pkix-cert")
            return

        if path == "/":
            self.path = "/index.html"
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()


def main():
    cleanup_guacamole_drive_sessions(force=True)
    host = "" if BIND_ADDRESS in ("*", "+", "0.0.0.0") else BIND_ADDRESS
    server = ThreadingHTTPServer((host, PORT), EnvPortalHandler)
    server.daemon_threads = True

    def shutdown(signum=None, frame=None):
        print("")
        print("Stopping EnvPortal server...")
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    print("=================================================")
    print(" EnvPortal - Python Server")
    display_bind = "0.0.0.0" if BIND_ADDRESS in ("*", "+", "0.0.0.0") else BIND_ADDRESS
    print(f" Binding:   http://{display_bind}:{PORT}/")
    print(f" Local URL: http://localhost:{PORT}/index.html")
    if display_bind == "0.0.0.0":
        lan_urls = [f"http://{ip}:{PORT}/index.html" for ip in local_lan_ips()]
        if lan_urls:
            for index, url in enumerate(lan_urls):
                label = "LAN URL:  " if index == 0 else "          "
                print(f" {label} {url}")
        else:
            print(f" LAN URL:   http://<this-machine-ip>:{PORT}/index.html")
    print(" Press Ctrl+C to stop.")
    print("=================================================")
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
        print("EnvPortal server stopped.")


if __name__ == "__main__":
    main()
