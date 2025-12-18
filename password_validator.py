"""Password strength validation utilities."""
import re


def validate_password_strength(password):
    """
    Validate password meets minimum security requirements.
    
    Requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        return False, "Password must contain at least one special character (!@#$%^&* etc.)"
    
    return True, None


def get_password_requirements():
    """Return user-friendly list of password requirements."""
    return [
        "At least 8 characters long",
        "Contains uppercase and lowercase letters",
        "Contains at least one number",
        "Contains at least one special character (!@#$%^&* etc.)"
    ]
