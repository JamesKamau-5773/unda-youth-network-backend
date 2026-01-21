"""
Developer-only hidden routes for debugging and build inspection.
Only accessible with the correct secret key.
"""

from flask import Blueprint, jsonify, request, abort, render_template_string
import os
import sys
from datetime import datetime, timezone
from models import db, User, Champion, Event, BlogPost, MentalHealthAssessment, EventParticipation
import sqlalchemy

dev = Blueprint('dev', __name__, url_prefix='/__dev__')

# Secret key that must be provided to access these routes
DEV_SECRET_KEY = os.environ.get('DEV_SECRET_KEY', 'your-secret-dev-key-change-this')


def require_dev_key(f):
    """Decorator to require the dev secret key"""
    def decorated_function(*args, **kwargs):
        key = request.args.get('key') or request.headers.get('X-Dev-Key')
        if not key or key != DEV_SECRET_KEY:
            abort(404)  # Return 404 instead of 403 to hide the route's existence
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@dev.route('/info')
@require_dev_key
def build_info():
    """Get comprehensive build and system information"""
    
    # Get database stats
    db_stats = {}
    try:
        db_stats = {
            'users_count': User.query.count(),
            'champions_count': Champion.query.count(),
            'events_count': Event.query.count() if hasattr(db, 'metadata') and 'events' in [t.name for t in db.metadata.sorted_tables] else 'N/A',
            'blog_posts_count': BlogPost.query.count() if hasattr(db, 'metadata') and 'blog_posts' in [t.name for t in db.metadata.sorted_tables] else 'N/A',
        }
    except Exception as e:
        db_stats['error'] = str(e)
    
    # Get environment info (mask sensitive data)
    env_vars = {}
    for key in os.environ.keys():
        if any(secret in key.upper() for secret in ['PASSWORD', 'SECRET', 'KEY', 'TOKEN', 'DSN']):
            env_vars[key] = '***MASKED***'
        else:
            env_vars[key] = os.environ.get(key)
    
    # Get installed packages
    try:
        import pkg_resources
        installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    except:
        installed_packages = {'error': 'Unable to retrieve packages'}
    
    # Get database tables using a short-lived connection to avoid leaks
    db_tables = []
    try:
        with db.engine.connect() as conn:
            inspector = sqlalchemy.inspect(conn)
            db_tables = inspector.get_table_names()
    except Exception as e:
        db_tables = [f'Error: {str(e)}']
    
    info = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'system': {
            'python_version': sys.version,
            'platform': sys.platform,
            'executable': sys.executable,
        },
        'environment': env_vars,
        'database': {
            'url': os.environ.get('DATABASE_URL', 'Not set')[:20] + '***' if os.environ.get('DATABASE_URL') else 'Not set',
            'tables': db_tables,
            'stats': db_stats,
        },
        'installed_packages': installed_packages,
        'flask': {
            'env': os.environ.get('FLASK_ENV', 'production'),
            'debug': os.environ.get('FLASK_DEBUG', 'False'),
        }
    }
    
    return jsonify(info)


@dev.route('/dashboard')
@require_dev_key
def dashboard():
    """HTML dashboard for developers"""
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Developer Dashboard - UNDA</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
            h2 { color: #555; margin-top: 30px; }
            .card {
                background: white;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .stat {
                display: inline-block;
                margin: 10px 20px 10px 0;
                padding: 15px 25px;
                background: #4CAF50;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            .stat-label { font-size: 12px; opacity: 0.9; }
            .stat-value { font-size: 24px; }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th { background-color: #4CAF50; color: white; }
            tr:hover { background-color: #f5f5f5; }
            .masked { color: #999; font-style: italic; }
            code {
                background: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
            .warning {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
            }
            a.btn {
                display: inline-block;
                padding: 10px 20px;
                background: #2196F3;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 5px;
            }
            a.btn:hover { background: #0b7dda; }
        </style>
    </head>
    <body>
        <h1>🔧 Developer Dashboard</h1>
        <div class="warning">
            <strong>⚠️ Warning:</strong> This is a hidden developer route. 
            Do not share the access URL with anyone. Keep your DEV_SECRET_KEY secure.
        </div>
        
        <div class="card">
            <h2>Quick Actions</h2>
            <a href="/__dev__/info?key={{ key }}" class="btn">View JSON Info</a>
            <a href="/__dev__/structure?key={{ key }}" class="btn">View File Structure</a>
            <a href="/__dev__/routes?key={{ key }}" class="btn">View All Routes</a>
        </div>
        
        <div class="card">
            <h2>Database Statistics</h2>
            <div class="stat">
                <div class="stat-label">Users</div>
                <div class="stat-value">{{ db_stats.users }}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Champions</div>
                <div class="stat-value">{{ db_stats.champions }}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Tables</div>
                <div class="stat-value">{{ db_stats.tables }}</div>
            </div>
        </div>
        
        <div class="card">
            <h2>System Information</h2>
            <p><strong>Python Version:</strong> <code>{{ system.python_version }}</code></p>
            <p><strong>Platform:</strong> <code>{{ system.platform }}</code></p>
            <p><strong>Flask Environment:</strong> <code>{{ system.flask_env }}</code></p>
            <p><strong>Timestamp:</strong> <code>{{ timestamp }}</code></p>
        </div>
        
        <div class="card">
            <h2>Environment Variables</h2>
            <table>
                <tr><th>Variable</th><th>Value</th></tr>
                {% for key, value in env_vars.items() %}
                <tr>
                    <td><code>{{ key }}</code></td>
                    <td>{% if '***' in value %}<span class="masked">{{ value }}</span>{% else %}<code>{{ value[:50] }}{% if value|length > 50 %}...{% endif %}</code>{% endif %}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """
    
    # Get database stats
    db_stats_data = {
        'users': User.query.count(),
        'champions': Champion.query.count(),
        'tables': len(sqlalchemy.inspect(db.engine).get_table_names()),
    }
    
    # Get environment variables (masked)
    env_vars = {}
    for key in sorted(os.environ.keys()):
        if any(secret in key.upper() for secret in ['PASSWORD', 'SECRET', 'KEY', 'TOKEN', 'DSN']):
            env_vars[key] = '***MASKED***'
        else:
            env_vars[key] = os.environ.get(key, '')
    
    system_info = {
        'python_version': sys.version.split()[0],
        'platform': sys.platform,
        'flask_env': os.environ.get('FLASK_ENV', 'production'),
    }
    
    return render_template_string(
        html,
        key=request.args.get('key'),
        db_stats=db_stats_data,
        env_vars=env_vars,
        system=system_info,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@dev.route('/structure')
@require_dev_key
def file_structure():
    """Display the project file structure"""
    
    def get_directory_structure(path, prefix="", max_depth=3, current_depth=0):
        """Recursively get directory structure"""
        if current_depth >= max_depth:
            return []
        
        items = []
        try:
            entries = sorted(os.listdir(path))
            for entry in entries:
                # Skip common ignored directories
                if entry in ['.git', '__pycache__', 'node_modules', '.venv', 'venv', 'instance']:
                    continue
                
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    items.append(f"{prefix}📁 {entry}/")
                    items.extend(get_directory_structure(full_path, prefix + "  ", max_depth, current_depth + 1))
                else:
                    items.append(f"{prefix}📄 {entry}")
        except PermissionError:
            items.append(f"{prefix}❌ Permission Denied")
        
        return items
    
    # Get project root (assuming app.py is in root)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    structure = get_directory_structure(project_root)
    
    return jsonify({
        'project_root': project_root,
        'structure': structure
    })


@dev.route('/routes')
@require_dev_key
def list_routes():
    """List all registered Flask routes"""
    from flask import current_app
    
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule),
        })
    
    # Sort by path
    routes.sort(key=lambda x: x['path'])
    
    return jsonify({'routes': routes, 'count': len(routes)})


@dev.route('/logs')
@require_dev_key
def view_logs():
    """View recent application logs (if available)"""
    # This is a placeholder - you can implement log viewing based on your logging setup
    return jsonify({
        'message': 'Log viewing not yet implemented',
        'suggestion': 'Check your hosting platform logs or implement custom logging'
    })


@dev.route('/simulate_mpesa', methods=['GET', 'POST'])
@require_dev_key
def simulate_mpesa():
    """Simulate M-Pesa idempotency events server-side.

    This endpoint is intentionally developer-only (requires DEV_SECRET_KEY).
    It will call the idempotency helpers (reserve/update) to generate
    Prometheus metrics for: requests, reserved, duplicate, success, failed.

    Query params:
      - count: number of unique reservation attempts to execute (default 100)
      - duplicates: number of duplicate/replay attempts to fire (default 20)
      - sleep_ms: optional per-reservation sleep in ms to simulate processing
    """
    try:
        count = int(request.args.get('count', 100))
    except Exception:
        count = 100
    try:
        duplicates = int(request.args.get('duplicates', 20))
    except Exception:
        duplicates = 20
    try:
        sleep_ms = int(request.args.get('sleep_ms', 5))
    except Exception:
        sleep_ms = 5

    # Import idempotency helpers lazily to avoid import-time side effects
    try:
        from utils.idempotency import reserve_key, update_key
    except Exception as e:
        return jsonify({'error': 'Failed to import idempotency utilities', 'detail': str(e)}), 500

    import uuid, random, time

    reserved_keys = []
    results = {'attempted': 0, 'reserved': 0, 'duplicates_detected': 0, 'marked_success': 0}

    for i in range(count):
        # deterministic-ish phone and amount for realism
        phone = f"2547{random.randint(10000000,99999999)}"
        amount = random.randint(10, 1000)
        key = str(uuid.uuid4())
        results['attempted'] += 1
        ok = reserve_key(key, meta={'phone': phone, 'amount': amount})
        if ok:
            reserved_keys.append(key)
            results['reserved'] += 1
            # simulate immediate success for most reservations
            update_key(key, status='success', response={'CheckoutRequestID': f'MOCK-{key[:8]}'})
            results['marked_success'] += 1
        else:
            results['duplicates_detected'] += 1

        # small sleep to spread events so Prometheus scrapes can observe changes
        if sleep_ms:
            time.sleep(sleep_ms / 1000.0)

    # Fire some duplicate attempts by attempting to reserve existing keys
    dup_hits = 0
    for i in range(duplicates):
        if reserved_keys:
            target = random.choice(reserved_keys)
            dup = reserve_key(target)
            if not dup:
                dup_hits += 1

    results['duplicate_attempts_sent'] = duplicates
    results['duplicate_hits'] = dup_hits

    return jsonify(results)
