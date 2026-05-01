import csv
import ctypes
from ctypes import wintypes
import json
import os
import re
import signal
import ssl
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
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
PORT = int(CONFIG.get("PORT", "8080"))
BIND_ADDRESS = CONFIG.get("BIND_ADDRESS", "0.0.0.0")
AUTH_PASSWORD = CONFIG.get("AUTH_PASSWORD", "nho1234567")
RDP_SIGN_THUMBPRINT = CONFIG.get("RDP_SIGN_THUMBPRINT", "").replace(" ", "")
RDP_CERT_SUBJECT = CONFIG.get("RDP_CERT_SUBJECT", "CN=EnvPortal RDP Signing")
GUACAMOLE_URL = CONFIG.get("GUACAMOLE_URL", "").rstrip("/")
GUACAMOLE_PUBLIC_URL = CONFIG.get("GUACAMOLE_PUBLIC_URL", "").rstrip("/")
GUACAMOLE_USERNAME = CONFIG.get("GUACAMOLE_USERNAME", "")
GUACAMOLE_PASSWORD = CONFIG.get("GUACAMOLE_PASSWORD", "")


def json_bytes(payload):
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def parse_form(body):
    return {k: v[0] if v else "" for k, v in urllib.parse.parse_qs(body, keep_blank_values=True).items()}


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


def build_guacamole_uri(target, user="", password=""):
    target = str(target or "").strip()
    user = str(user or "").strip()
    password = str(password or "")
    authority = target
    if user:
        credential = urllib.parse.quote(user, safe="")
        if password:
            credential += ":" + urllib.parse.quote(password, safe="")
        authority = credential + "@" + target
    params = urllib.parse.urlencode({
        "ignore-cert": "true",
        "security": "any",
        "disable-audio": "true",
        "enable-wallpaper": "false",
    })
    return f"rdp://{authority}/?{params}"


def public_guacamole_url(request_host=""):
    if GUACAMOLE_PUBLIC_URL:
        return GUACAMOLE_PUBLIC_URL
    if not GUACAMOLE_URL:
        return ""
    parsed = urllib.parse.urlparse(GUACAMOLE_URL)
    if parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        return GUACAMOLE_URL
    host_header = str(request_host or "").split(":")[0].strip()
    if not host_header or host_header in ("localhost", "127.0.0.1", "::1"):
        return GUACAMOLE_URL
    netloc = host_header
    if parsed.port:
        netloc += f":{parsed.port}"
    return urllib.parse.urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))


def guacamole_quickconnect(target, user="", password="", public_url=""):
    quickconnect_uri = build_guacamole_uri(target, user, password)
    display_url = public_url or GUACAMOLE_URL
    if not GUACAMOLE_URL:
        return {
            "ok": False,
            "mode": "disabled",
            "guacamoleUrl": "",
            "quickconnectUri": quickconnect_uri,
            "message": "Guacamole is not configured.",
        }

    fallback = {
        "ok": True,
        "mode": "manual",
        "guacamoleUrl": display_url,
        "quickconnectUri": quickconnect_uri,
        "message": "Open Guacamole and paste the QuickConnect URI.",
    }
    if not GUACAMOLE_USERNAME or not GUACAMOLE_PASSWORD:
        return fallback

    try:
        token_response = http_post_form(
            f"{GUACAMOLE_URL}/api/tokens",
            {"username": GUACAMOLE_USERNAME, "password": GUACAMOLE_PASSWORD},
        )
        token = token_response.get("authToken", "")
        if not token:
            return {**fallback, "message": "Guacamole token was not returned."}
        created = http_post_form(
            f"{GUACAMOLE_URL}/api/session/ext/quickconnect/create?token={urllib.parse.quote(token)}",
            {"uri": quickconnect_uri},
        )
        identifier = created.get("identifier", "") if isinstance(created, dict) else ""
        if not identifier:
            return {**fallback, "message": "Guacamole QuickConnect did not return an identifier."}
        return {
            "ok": True,
            "mode": "direct",
            "url": f"{display_url}/#/client/{urllib.parse.quote(identifier)}?token={urllib.parse.quote(token)}",
            "guacamoleUrl": display_url,
            "quickconnectUri": quickconnect_uri,
            "message": "",
        }
    except Exception as exc:
        return {**fallback, "message": str(exc)}


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
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_download(self, payload, filename, content_type="application/x-rdp"):
        quoted = urllib.parse.quote(filename)
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quoted}")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        path = urllib.parse.urlparse(self.path).path

        if path == "/auth.jsp":
            form = parse_form(body)
            self.send_bytes(b"OK" if form.get("pwd", "") == AUTH_PASSWORD else b"NG")
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

        update_map = {
            "/update_csv.jsp": "data.csv",
            "/update_rdp.jsp": "rdp.csv",
            "/update_tags.jsp": "tags.json",
        }
        if path in update_map:
            (BASE_DIR / update_map[path]).write_text(body, encoding="utf-8-sig", newline="")
            self.send_bytes(b"success")
            return

        self.send_bytes(b"Not Found", status=404)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

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
            self.send_bytes(json_bytes({
                "guacamoleEnabled": bool(GUACAMOLE_URL),
                "guacamoleUrl": public_guacamole_url(self.headers.get("Host", "")),
                "guacamoleAutoLogin": bool(GUACAMOLE_URL and GUACAMOLE_USERNAME and GUACAMOLE_PASSWORD),
            }), "application/json; charset=utf-8")
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
        print(f" LAN URL:   http://<this-machine-ip>:{PORT}/index.html")
    print(" Press Ctrl+C to stop.")
    print("=================================================")
    try:
        if sys.platform.startswith("win"):
            os.startfile(f"http://localhost:{PORT}/index.html")
    except Exception:
        pass
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
        print("EnvPortal server stopped.")


if __name__ == "__main__":
    main()
