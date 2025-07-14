#!/bin/bash
echo "Applying database migrations..."
python database.py
echo "Starting bot..."
python main.py
