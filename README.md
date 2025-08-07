# SQLite Database

<div align="center">

![GitHub forks](https://img.shields.io/github/forks/RimuEirnarn/sqlite_database?style=social)
![GitHub Repo stars](https://img.shields.io/github/stars/RimuEirnarn/sqlite_database?style=social)

![GitHub closed issues](https://img.shields.io/github/issues-closed-raw/RimuEirnarn/sqlite_database)
![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/RimuEirnarn/sqlite_database)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/RimuEirnarn/sqlite_database)
![GitHub all releases](https://img.shields.io/github/downloads/RimuEirnarn/sqlite_database/total)
![GitHub Workflow(pylint) Status](https://img.shields.io/github/actions/workflow/status/RimuEirnarn/sqlite_database/pylint.yml?label=lint)
![GitHub Workflow(pytest) Status](https://img.shields.io/github/actions/workflow/status/RimuEirnarn/sqlite_database/pytest.yml?label=tests)
![GitHub Workflow(pypi) Status](https://img.shields.io/github/actions/workflow/status/RimuEirnarn/sqlite_database/python-publish.yml)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/RimuEirnarn/sqlite_database)
[![Documentation Status](https://readthedocs.org/projects/sqlite-database/badge/?version=latest)](https://sqlite-database.readthedocs.io/en/latest/?badge=latest)
![GitHub](https://img.shields.io/github/license/RimuEirnarn/sqlite_database)
![CodeFactor Grade](https://img.shields.io/codefactor/grade/github/RimuEirnarn/sqlite_database)

![PyPI - Format](https://img.shields.io/pypi/format/sqlite-database)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/sqlite-database)
![PyPI - Implementation](https://img.shields.io/pypi/implementation/sqlite-database)
![PyPI - Downloads](https://img.shields.io/pypi/dm/sqlite-database?label=%28PyPI%29%20downloads)
![PyPI - Downloads Daily](https://img.shields.io/pypi/dd/sqlite_database?label=(PyPI)%20downloads%20daily)


</div>

**SQLite Database** is a lightweight, developer-friendly wrapper for SQLite—designed to feel as intuitive as Laravel's Eloquent ORM, but in Python.

> [!WARNING]
> ⚠️ This library is still pre-1.0, which means it's not optimized for high performance or low memory usage (yet). Use with care. If you run into serious issues, feel free to open an issue—we’re listening.

---

## 🚀 Usage & Demo

Curious how it works in action?  
Check out the live example here: [sqlite-database demo](https://github.com/RimuEirnarn/sqlite_database_demo)

---

## 📦 Installation

The library is available via PyPI:

```sh
pip install sqlite-database
```

Prefer to install directly from GitHub? You can still do this the old-school way:

```sh
pip install https://github.com/RimuEirnarn/sqlite_database/archive/refs/tags/<latest-version>.zip
```

---

## ✨ Features

A quick feature overview is available in [Features.md](https://github.com/RimuEirnarn/sqlite_database/blob/main/docs/SimpleGuide.md)

Or check out the full short docs at:  
📚 [sqlite-database.rtfd.io](https://sqlite-database.rtfd.io/)

---

## 📖 Origin Story & Acknowledgements

Wondering why this exists?  
Read the [History.md](History.md) to learn what led to the birth of this project.

> Pre-contributor: just ChatGPT—so blame the AI if anything’s weird.

---

## 🤝 Contributing

Found a bug? Got an idea? Want to improve something?

- Open an issue for anything noteworthy.
- PRs are welcome—as long as they align with the project's vision and design goals.

---

## 🛠️ Development Setup

Thanks for considering contributing to `sqlite_database`! Here's what you'll need:

- **Testing**: `pytest`
- **Linting**: `pylint`
- **Docs**: `sphinx`

Dependencies are split between:
- `dev-requirements.txt` (core development)
- `docs-requirements.txt` (documentation)

To get started:

```sh
git clone https://github.com/RimuEirnarn/sqlite_database
cd sqlite_database

python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

pip install -r ./dev-requirements.txt
./bin/check.sh
```

The `check.sh` script will run:

```sh
pylint --rcfile ./dev-config/pylint.toml sqlite_database
pytest --config-file ./dev-config/pytest.ini
```

Simple and clean.

---

## 📄 License

This project is licensed under the **BSD 3-Clause "New" or "Revised" License**.

Read the full license here:  
[LICENSE](https://github.com/RimuEirnarn/sqlite_database/blob/main/LICENSE)

---
