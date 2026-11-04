#!/bin/bash
echo "Starting WolfFeed portable app..."
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Please install Python 3.8+"
    exit 1
fi
pip3 install -r requirements.txt
python3 app.py
