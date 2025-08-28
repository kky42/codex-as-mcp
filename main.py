import json
import os
import pathlib
import subprocess
import sys
import shutil

CONFIG_FILE = "env.config.json"
VENV_DIR = ".venv"

def ensure_env():
    config_path = pathlib.Path(CONFIG_FILE)
    if config_path.exists():
        with config_path.open() as f:
            data = json.load(f)
        python_cmd = data.get("python", "python3")
        python_path = data.get("python_path")
        venv_dir = data.get("venv_path", VENV_DIR)
        deps = data.get("dependencies", {})
        venv_python = pathlib.Path(venv_dir) / ("Scripts" if os.name == "nt" else "bin") / "python"
        if pathlib.Path(sys.executable).resolve() != venv_python.resolve():
            if not venv_python.exists():
                if python_path:
                    python_exe = python_path
                else:
                    python_exe = shutil.which(python_cmd) or sys.executable
                subprocess.check_call([str(python_exe), "-m", "venv", venv_dir])
            os.execv(str(venv_python), [str(venv_python), *sys.argv])
        if deps:
            subprocess.check_call([str(venv_python), "-m", "ensurepip", "--upgrade"])
            packages = [f"{name}=={ver}" for name, ver in deps.items()]
            subprocess.check_call([str(venv_python), "-m", "pip", "install", *packages])
    else:
        lock_file = pathlib.Path("uv.lock")
        if lock_file.exists():
            try:
                subprocess.check_call(["uv", "pip", "install", "-r", str(lock_file)])
            except FileNotFoundError:
                print("未找到 uv 命令，无法根据 uv.lock 安装依赖", file=sys.stderr)

def main():
    ensure_env()
    print("Hello from codex-as-mcp!")

if __name__ == "__main__":
    main()

