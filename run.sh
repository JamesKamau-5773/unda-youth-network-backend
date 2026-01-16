#!/bin/bash
# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Decide migration / cleanup behavior according to CLEAN_BREAK_MODE
# Modes:
#  - skip_migrations : do not run migrations (useful during build to break migration loop)
#  - cleanup_then_upgrade : run data cleanup, then run migrations (use on first start)
#  - (default) : run migrations as usual
CLEAN_BREAK_MODE=${CLEAN_BREAK_MODE:-}

if [ "${CLEAN_BREAK_MODE}" = "skip_migrations" ]; then
    echo "CLEAN_BREAK_MODE=skip_migrations — skipping database migrations as requested."
elif [ "${CLEAN_BREAK_MODE}" = "cleanup_then_upgrade" ]; then
    echo "CLEAN_BREAK_MODE=cleanup_then_upgrade — running data cleanup before migrations."
    if [ -x "$(pwd)/scripts/cleanup_orphans.sh" ]; then
        scripts/cleanup_orphans.sh
    else
        echo "Warning: cleanup script not found or not executable: scripts/cleanup_orphans.sh"
    fi
    echo "Running database migrations..."
    flask db upgrade
else
    echo "Running database migrations..."
    flask db upgrade
fi

# Start the application
echo "Starting Unda Youth Network application..."
python app.py
