@echo off
call .venv\Scripts\activate.bat

pylint --rcfile ./dev-config/pylint.toml sqlite_database
pytest --config-file ./dev-config/pytest.ini