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
    echo "Running database migrations... (via scripts/run_migrations.sh)"
    scripts/run_migrations.sh
else
    echo "Running database migrations... (via scripts/run_migrations.sh)"
    scripts/run_migrations.sh
fi

# Start the application
echo "Starting Unda Youth Network application..."
# Defensive start: kill any python process that is stopped (T) but still holding port 5000
# and avoid orphaned/stopped processes causing TCP accepts with no responses.
if command -v ss >/dev/null 2>&1; then
    # find PIDs listening on 127.0.0.1:5000
    PIDS=$(ss -ltnp | grep ':5000' | sed -n 's/.*pid=\([0-9]*\),.*/\1/p' || true)
    for p in $PIDS; do
        if [ -n "$p" ]; then
            state=$(ps -o stat= -p "$p" 2>/dev/null || true)
            if echo "$state" | grep -q 'T'; then
                echo "Killing stale process $p holding :5000 (state=$state)"
                kill -9 "$p" 2>/dev/null || true
            fi
        fi
    done
fi

# Start app normally (foreground)
python app.py
