import os
import shlex
import subprocess
import sys
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
    start_guacamole_if_available()
    import server
    server.main()


if __name__ == "__main__":
    main()
