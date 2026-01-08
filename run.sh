#!/bin/bash
# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Start the application
echo "Starting Unda Youth Network application..."
python app.py
