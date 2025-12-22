from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

# Initialize Limiter here to avoid circular imports
# More generous limits for development, stricter for production
is_production = os.environ.get('FLASK_ENV') == 'production'
default_limits = ["1000 per day", "200 per hour"] if is_production else ["10000 per day", "1000 per hour"]
limiter = Limiter(key_func=get_remote_address, default_limits=default_limits, storage_uri="memory://")