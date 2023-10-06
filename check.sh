#!/bin/sh

if [ ! -f .venv/bin/activate ]; then
    echo "Cannot found .venv: please do python3 -m venv .venv"
    echo "Make sure your python version is python3.11 or later"
    exit 1
fi

. .venv/bin/activate

pylint --rcfile pylint.toml sqlite_database
if [ ! "$?" = 0 ]; then
    echo "Pylint error"
    exit 1
fi
pytest
