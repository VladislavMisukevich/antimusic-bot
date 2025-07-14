#!/bin/bash
echo "Force reinstalling dependencies..."
pip install --force-reinstall -r requirements.txt

echo "Applying database migrations..."
python database.py

echo "Starting bot..."
python main.py
