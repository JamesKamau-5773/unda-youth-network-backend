from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize Limiter here to avoid circular imports
limiter = Limiter(key_func=get_remote_address)