import os
import shlex
import socket
import subprocess
import sys
import urllib.parse
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def docker_desktop_candidates():
    candidates = []
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    docker_path = Path(program_files) / "Docker" / "Docker" / "resources" / "bin" / "docker.exe"
    compose_path = Path(program_files) / "Docker" / "Docker" / "resources" / "bin" / "docker-compose.exe"
    if docker_path.exists():
        candidates.append([str(docker_path), "compose"])
    if compose_path.exists():
        candidates.append([str(compose_path)])
    return candidates


def wsl_path(path):
    resolved = Path(path).resolve()
    drive = resolved.drive.rstrip(":").lower()
    parts = [part for part in resolved.parts[1:]]
    return "/mnt/" + drive + "/" + "/".join(part.replace("\\", "/") for part in parts)


def docker_command():
    checks = [
        (["docker", "compose"], ["docker", "compose", "version"], "windows"),
        (["docker-compose"], ["docker-compose", "--version"], "windows"),
    ]
    for candidate in docker_desktop_candidates():
        if len(candidate) == 2:
            checks.append((candidate, candidate + ["version"], "windows"))
        else:
            checks.append((candidate, candidate + ["--version"], "windows"))

    for command, check, kind in checks:
        try:
            subprocess.run(check, cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return {"kind": kind, "command": command}
        except Exception:
            continue

    wsl_check = "command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1"
    try:
        subprocess.run(["wsl.exe", "-e", "sh", "-lc", wsl_check], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return {"kind": "wsl", "command": ["docker", "compose"]}
    except Exception:
        pass
    return None


def load_env_value(name, default=""):
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return default
    for line in env_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        if key.strip() == name:
            return value.strip()
    return default


def env_int(name, default):
    try:
        return int(load_env_value(name, str(default)))
    except ValueError:
        return default


def guacamole_port():
    for name in ("GUACAMOLE_PUBLIC_URL", "GUACAMOLE_URL"):
        value = load_env_value(name, "")
        if not value:
            continue
        parsed = urllib.parse.urlparse(value)
        if parsed.port:
            return parsed.port
        if parsed.scheme == "https":
            return 443
        if parsed.scheme == "http":
            return 80
    return 8088


def is_windows_admin():
    if os.name != "nt":
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_windows_firewall_ports(ports):
    if os.name != "nt":
        return
    unique_ports = sorted({int(port) for port in ports if int(port) > 0})
    if not unique_ports:
        return

    if not is_windows_admin():
        print("Windows Firewall was not changed because this terminal is not running as Administrator.")
        print("Run these commands in an elevated PowerShell if LAN clients cannot connect:")
        for port in unique_ports:
            print(f"  New-NetFirewallRule -DisplayName 'EnvPortal TCP {port}' -Direction Inbound -Action Allow -Protocol TCP -LocalAddress Any -RemoteAddress Any -LocalPort {port} -Profile Any")
        return

    for port in unique_ports:
        display_name = f"EnvPortal TCP {port}"
        script = (
            f"$name = '{display_name}'; "
            "$rule = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue; "
            "if (-not $rule) { "
            f"New-NetFirewallRule -DisplayName $name -Direction Inbound -Action Allow -Protocol TCP -LocalAddress Any -RemoteAddress Any -LocalPort {port} -Profile Any | Out-Null; "
            "Write-Output 'created' "
            "} else { "
            "$rule | Set-NetFirewallRule -Enabled True -Direction Inbound -Action Allow -Profile Any | Out-Null; "
            "$rule | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -LocalAddress Any -RemoteAddress Any | Out-Null; "
            f"$rule | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -Protocol TCP -LocalPort {port} | Out-Null; "
            "Write-Output 'updated' "
            "}"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
            state = (result.stdout or "").strip() or "ok"
            print(f"Windows Firewall rule {display_name}: {state}")
        except Exception as exc:
            print(f"Windows Firewall rule {display_name} could not be verified: {exc}")


def check_local_tcp_port(port, label):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=1.5):
            print(f"{label} local port check: 127.0.0.1:{port} is reachable.")
            return True
    except Exception:
        print(f"{label} local port check: 127.0.0.1:{port} is not reachable yet.")
        return False


def start_guacamole_if_available():
    if load_env_value("GUACAMOLE_AUTO_START", "true").lower() not in ("1", "true", "yes", "on"):
        return
    compose_file = BASE_DIR / "docker-compose.guacamole.yml"
    if not compose_file.exists():
        return
    command = docker_command()
    if not command:
        print("Docker was not found in PATH, Docker Desktop, or WSL. Guacamole integration is disabled.")
        return
    try:
        if command["kind"] == "wsl":
            print("Starting Guacamole with Docker via WSL...")
            script = f"cd {shlex.quote(wsl_path(BASE_DIR))} && docker compose -f docker-compose.guacamole.yml up -d"
            subprocess.run(["wsl.exe", "-e", "sh", "-lc", script], cwd=BASE_DIR, check=True)
        else:
            print("Starting Guacamole with Docker...")
            print("Docker command:", " ".join(command["command"]))
            subprocess.run(command["command"] + ["-f", str(compose_file), "up", "-d"], cwd=BASE_DIR, check=True)
        check_local_tcp_port(guacamole_port(), "Guacamole")
    except Exception as exc:
        print(f"Guacamole auto-start failed: {exc}")


def install_requirements():
    requirements = BASE_DIR / "requirements.txt"
    if not requirements.exists():
        return
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements)])


def main():
    os.chdir(BASE_DIR)
    install_requirements()
    ensure_windows_firewall_ports([env_int("PORT", 8080), guacamole_port()])
    start_guacamole_if_available()
    import server
    server.main()


if __name__ == "__main__":
    main()
