---
name: python-use-uv
description: Use uv to manage Python virtual environments and dependencies
trigger: /python-use-uv
---

# /python-use-uv

Manage Python virtual environments and dependencies with [uv](https://docs.astral.sh/uv/), the fast Python package manager.

## Python Environment Rule

Always use one of the following when running Python commands or scripts:

- Prefix commands with `uv run`: `uv run python script.py`, `uv run pytest`, etc.
- Or activate the virtual environment first: `source .venv/bin/activate`

```bash
# ✅ GOOD
uv run python src/ls_mlkit/util/scheduler.py
uv run pytest tests/

# ✅ ALSO GOOD
source .venv/bin/activate
python src/ls_mlkit/util/scheduler.py

# ❌ BAD
python script.py
pip install package
```

Prefer `uv run` for one-off commands and `source .venv/bin/activate` for interactive sessions.

## Usage

```
/python-use-uv                          # create .venv in current dir, install from pyproject.toml or requirements.txt
/python-use-uv --python 3.12            # specify Python version for venv
/python-use-uv --no-venv                # skip venv creation, just install deps in current env
/python-use-uv add <package>            # add a dependency (uv add)
/python-use-uv remove <package>         # remove a dependency (uv remove)
/python-use-uv sync                     # sync environment from lockfile
/python-use-uv run <command>            # run command inside venv via uv run
/python-use-uv compile                  # compile requirements.in → requirements.txt
/python-use-uv upgrade <package>        # upgrade a specific package
/python-use-uv upgrade                  # upgrade all packages
```

## What You Must Do When Invoked

### Step 1 - Ensure uv is installed

```bash
if ! command -v uv &>/dev/null; then
    echo "uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
uv --version
```

### Step 2 - Create virtual environment (unless --no-venv)

If `.venv/` already exists, skip creation. Otherwise:

```bash
uv venv VENV_PYTHON_FLAG
```

Replace `VENV_PYTHON_FLAG` with `--python <version>` if the user specified one, otherwise omit it. Default location is `.venv/`.

### Step 3 - Install dependencies

If `pyproject.toml` exists with `[project]` or `[tool.uv]`:
```bash
uv sync
```

If `requirements.txt` exists (but no pyproject.toml):
```bash
uv pip install -r requirements.txt
```

If neither exists and no packages specified, ask the user what to install.

### Step 4 - Handle subcommands

**add** - Add and install a dependency:
```bash
uv add PACKAGE_NAME
```
This updates `pyproject.toml` (or `requirements.txt`) and installs the package.

**remove** - Remove a dependency:
```bash
uv remove PACKAGE_NAME
```

**sync** - Sync environment with lockfile:
```bash
uv sync
```

**run** - Run inside the venv:
```bash
uv run COMMAND_OR_SCRIPT
```

**compile** - Compile requirements:
```bash
uv pip compile requirements.in -o requirements.txt
```

**upgrade** - Upgrade packages:
```bash
uv lock --upgrade-package PACKAGE_NAME   # single, with pyproject.toml
uv lock --upgrade                         # all, with pyproject.toml
uv pip install --upgrade PACKAGE_NAME     # single, with requirements.txt
uv pip install --upgrade -r requirements.txt  # all, with requirements.txt
```

### Step 5 - Report

Print the venv location, Python version, and installed packages:
```bash
uv run python --version
uv pip list
```

## Notes

- `uv run` is the primary way to execute Python commands — it auto-manages the venv, no activation needed
- Use `uv add` to install packages (not `uv pip install`), it tracks dependencies in `pyproject.toml`
- The venv is created in `.venv/` by default — add it to `.gitignore`
- For projects without `pyproject.toml`, `uv pip install` is the fallback