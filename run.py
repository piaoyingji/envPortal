import os
import shlex
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def docker_desktop_base_dirs():
    values = []
    for env_name in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)", "LocalAppData"):
        root = os.environ.get(env_name)
        if not root:
            continue
        path = Path(root) / "Docker" / "Docker"
        if path not in values:
            values.append(path)
    return values


def docker_desktop_executable():
    for base_dir in docker_desktop_base_dirs():
        exe = base_dir / "Docker Desktop.exe"
        if exe.exists():
            return exe
    return None


def docker_cli_candidates():
    candidates = [["docker"], ["docker-compose"]]
    for base_dir in docker_desktop_base_dirs():
        docker_path = base_dir / "resources" / "bin" / "docker.exe"
        compose_path = base_dir / "resources" / "bin" / "docker-compose.exe"
        if docker_path.exists():
            candidates.append([str(docker_path)])
        if compose_path.exists():
            candidates.append([str(compose_path)])
    return candidates


def docker_subprocess_env(command=None):
    env = os.environ.copy()
    paths = []
    if command and command.get("kind") == "windows":
        executable = Path(command["command"][0])
        if executable.is_absolute() and executable.parent.exists():
            paths.append(str(executable.parent))
    for base_dir in docker_desktop_base_dirs():
        bin_dir = base_dir / "resources" / "bin"
        if bin_dir.exists():
            paths.append(str(bin_dir))
    current_path = env.get("PATH", "")
    existing = {item.lower() for item in current_path.split(os.pathsep) if item}
    prepend = [item for item in paths if item.lower() not in existing]
    if prepend:
        env["PATH"] = os.pathsep.join(prepend + [current_path])
    return env


def wsl_path(path):
    resolved = Path(path).resolve()
    drive = resolved.drive.rstrip(":").lower()
    parts = [part for part in resolved.parts[1:]]
    return "/mnt/" + drive + "/" + "/".join(part.replace("\\", "/") for part in parts)


def docker_command():
    checks = []
    for candidate in docker_cli_candidates():
        if Path(candidate[0]).name.lower().startswith("docker-compose"):
            checks.append((candidate, candidate + ["--version"], "windows"))
        else:
            checks.append((candidate + ["compose"], candidate + ["compose", "version"], "windows"))

    for command, check, kind in checks:
        try:
            subprocess.run(check, cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=docker_subprocess_env({"kind": kind, "command": command}), check=True)
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


def docker_engine_ready(command):
    if not command:
        return False
    try:
        if command["kind"] == "wsl":
            result = subprocess.run(
                ["wsl.exe", "-e", "sh", "-lc", "docker info >/dev/null 2>&1"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
        elif Path(command["command"][0]).name.lower().startswith("docker-compose"):
            result = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=docker_subprocess_env(command),
                timeout=8,
            )
        else:
            result = subprocess.run(
                [command["command"][0], "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=docker_subprocess_env(command),
                timeout=8,
            )
        return result.returncode == 0
    except Exception:
        return False


def start_docker_desktop_if_available():
    if os.name != "nt":
        return False
    exe = docker_desktop_executable()
    if not exe:
        return False
    try:
        print(f"Starting Docker Desktop: {exe}")
        subprocess.Popen([str(exe)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        return True
    except Exception as exc:
        print(f"Docker Desktop could not be started: {exc}")
        return False


def wait_for_docker_command(timeout_seconds=120):
    deadline = time.time() + timeout_seconds
    last_command = None
    while time.time() < deadline:
        command = docker_command()
        if command:
            last_command = command
            if docker_engine_ready(command):
                return command
        time.sleep(3)
    return last_command


def command_available(command):
    try:
        subprocess.run([command, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


def prompt_yes_no(message, default=False):
    if not sys.stdin or not sys.stdin.isatty():
        return default
    suffix = " [Y/n]: " if default else " [y/N]: "
    try:
        answer = input(message + suffix).strip().lower()
    except Exception:
        return default
    if not answer:
        return default
    return answer in ("y", "yes", "1")


def offer_docker_desktop_install():
    if os.name != "nt":
        return False
    if load_env_value("DOCKER_INSTALL_PROMPT", "true").lower() not in ("1", "true", "yes", "on"):
        return False
    if not command_available("winget"):
        print("Install Docker Desktop from https://www.docker.com/products/docker-desktop/ and run start.bat again.")
        return False
    if not prompt_yes_no("Docker Desktop is required for Guacamole. Install Docker Desktop now?", False):
        print("Guacamole integration is disabled until Docker Desktop is installed.")
        return False
    try:
        print("Installing Docker Desktop via winget...")
        subprocess.run(
            [
                "winget",
                "install",
                "-e",
                "--id",
                "Docker.DockerDesktop",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ],
            cwd=BASE_DIR,
            check=True,
        )
        print("Docker Desktop installation completed. Start Docker Desktop once, then run start.bat again.")
        return True
    except Exception as exc:
        print(f"Docker Desktop installation failed: {exc}")
        return False


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
        if load_env_value("FIREWALL_AUTO_ELEVATE", "true").lower() in ("1", "true", "yes", "on"):
            if elevate_firewall_rules(unique_ports):
                return
        print_firewall_commands(unique_ports)
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


def firewall_rule_script(ports):
    lines = [
        "$ErrorActionPreference = 'Stop'",
    ]
    for port in ports:
        display_name = f"EnvPortal TCP {port}"
        lines.extend([
            f"$name = '{display_name}'",
            "$rule = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue",
            "if (-not $rule) {",
            f"  New-NetFirewallRule -DisplayName $name -Direction Inbound -Action Allow -Protocol TCP -LocalAddress Any -RemoteAddress Any -LocalPort {port} -Profile Any | Out-Null",
            "  Write-Output \"created $name\"",
            "} else {",
            "  $rule | Set-NetFirewallRule -Enabled True -Direction Inbound -Action Allow -Profile Any | Out-Null",
            "  $rule | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -LocalAddress Any -RemoteAddress Any | Out-Null",
            f"  $rule | Get-NetFirewallPortFilter | Set-NetFirewallPortFilter -Protocol TCP -LocalPort {port} | Out-Null",
            "  Write-Output \"updated $name\"",
            "}",
        ])
    return "\n".join(lines) + "\n"


def elevate_firewall_rules(ports):
    temp_dir = BASE_DIR / ".tmp"
    temp_dir.mkdir(exist_ok=True)
    script_path = temp_dir / "envportal_firewall.ps1"
    script_path.write_text(firewall_rule_script(ports), encoding="utf-8-sig")
    try:
        print("Windows Firewall needs Administrator permission. Requesting elevation...")
        command = (
            f"Start-Process powershell "
            f"-ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"{script_path}\"' "
            "-Verb RunAs -Wait"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print("Windows Firewall elevated update completed.")
            return True
        print("Windows Firewall elevation was not completed.")
    except Exception as exc:
        print(f"Windows Firewall elevation failed: {exc}")
    print_firewall_commands(ports)
    return False


def print_firewall_commands(ports):
    print("Windows Firewall was not changed because this terminal is not running as Administrator.")
    print("Run these commands in an elevated PowerShell if LAN clients cannot connect:")
    for port in ports:
        print(f"  New-NetFirewallRule -DisplayName 'EnvPortal TCP {port}' -Direction Inbound -Action Allow -Protocol TCP -LocalAddress Any -RemoteAddress Any -LocalPort {port} -Profile Any")


def check_local_tcp_port(port, label):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=1.5):
            print(f"{label} local port check: 127.0.0.1:{port} is reachable.")
            return True
    except Exception:
        print(f"{label} local port check: 127.0.0.1:{port} is not reachable yet.")
        return False


def run_compose(command, args, capture=False):
    if command["kind"] == "wsl":
        script = f"cd {shlex.quote(wsl_path(BASE_DIR))} && docker compose {' '.join(shlex.quote(str(arg)) for arg in args)}"
        return subprocess.run(
            ["wsl.exe", "-e", "sh", "-lc", script],
            cwd=BASE_DIR,
            capture_output=capture,
            text=True,
            check=not capture,
        )
    return subprocess.run(
        command["command"] + [str(arg) for arg in args],
        cwd=BASE_DIR,
        capture_output=capture,
        text=True,
        env=docker_subprocess_env(command),
        check=not capture,
    )


def wait_for_http(url, timeout_seconds=60):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 500:
                    return True
        except Exception:
            time.sleep(2)
    return False


def print_compose_diagnostics(command, compose_file):
    print("Guacamole did not become reachable. Docker Compose diagnostics follow.")
    for args in (
        ["-f", compose_file, "ps"],
        ["-f", compose_file, "logs", "--tail=80", "guacamole"],
        ["-f", compose_file, "logs", "--tail=80", "guacamole-db"],
    ):
        result = run_compose(command, args, capture=True)
        output = ((result.stdout or "") + (result.stderr or "")).strip()
        print("")
        print(">", " ".join(["docker", "compose"] + [str(arg) for arg in args]))
        print(output or "(no output)")


def guacamole_schema_state(command, compose_file, timeout_seconds=45):
    query = (
        "SELECT CASE WHEN "
        "EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='guacamole_user' AND column_name='entity_id') "
        "AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='guacamole_user_group') "
        "AND EXISTS (SELECT 1 FROM pg_type WHERE typname='guacamole_entity_type') "
        "THEN 'ok' ELSE 'bad' END;"
    )
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = run_compose(
            command,
            [
                "-f",
                compose_file,
                "exec",
                "-T",
                "guacamole-db",
                "sh",
                "-lc",
                f"PGPASSWORD=guacamole_pass psql -U guacamole_user -d guacamole_db -tAc {shlex.quote(query)}",
            ],
            capture=True,
        )
        output = ((result.stdout or "") + (result.stderr or "")).strip().lower()
        if result.returncode == 0 and "ok" in output:
            return "ok"
        if result.returncode == 0 and "bad" in output:
            return "bad"
        time.sleep(3)
    return "unknown"


def reset_guacamole_volume_if_bad_schema(command, compose_file):
    if load_env_value("GUACAMOLE_RESET_BAD_DB", "true").lower() not in ("1", "true", "yes", "on"):
        return
    state = guacamole_schema_state(command, compose_file)
    if state == "ok":
        print("Guacamole database schema: ok")
        return
    if state == "unknown":
        print("Guacamole database schema could not be verified yet.")
        return

    print("Guacamole database schema is incompatible. Recreating EnvPortal Guacamole volume...")
    run_compose(command, ["-f", compose_file, "down", "-v"])
    run_compose(command, ["-f", compose_file, "up", "-d"])
    state = guacamole_schema_state(command, compose_file)
    print(f"Guacamole database schema after reset: {state}")


def start_guacamole_if_available():
    if load_env_value("GUACAMOLE_AUTO_START", "true").lower() not in ("1", "true", "yes", "on"):
        return
    compose_file = BASE_DIR / "docker-compose.guacamole.yml"
    if not compose_file.exists():
        return
    command = docker_command()
    if not command:
        if start_docker_desktop_if_available():
            print("Waiting for Docker Desktop to expose the Docker CLI...")
            command = wait_for_docker_command(env_int("DOCKER_WAIT_SECONDS", 120))
        if not command:
            print("Docker was not found in PATH, Docker Desktop, or WSL. Guacamole integration is disabled.")
            offer_docker_desktop_install()
            return
    if not docker_engine_ready(command):
        if start_docker_desktop_if_available():
            print("Waiting for Docker Desktop engine...")
            command = wait_for_docker_command(env_int("DOCKER_WAIT_SECONDS", 120)) or command
    if not docker_engine_ready(command):
        print("Docker CLI was found, but the Docker engine is not ready. Start Docker Desktop and run start.bat again.")
        return
    try:
        if command["kind"] == "wsl":
            print("Starting Guacamole with Docker via WSL...")
        else:
            print("Starting Guacamole with Docker...")
            print("Docker command:", " ".join(command["command"]))
        run_compose(command, ["-f", compose_file, "up", "-d"])
        reset_guacamole_volume_if_bad_schema(command, compose_file)
        port = guacamole_port()
        check_local_tcp_port(port, "Guacamole")
        url = f"http://127.0.0.1:{port}/guacamole/"
        print(f"Waiting for Guacamole: {url}")
        if wait_for_http(url, env_int("GUACAMOLE_WAIT_SECONDS", 60)):
            print(f"Guacamole is ready: {url}")
        else:
            print_compose_diagnostics(command, compose_file)
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
