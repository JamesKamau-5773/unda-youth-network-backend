````markdown
# Developer Routes - Hidden Access

This document describes the hidden developer routes that provide comprehensive access to the application's build, configuration, and system information.

## Security

These routes are **hidden** and only accessible with a secret key. They are designed for developer/admin use only.

### Setup

1. Set the `DEV_SECRET_KEY` environment variable:
   ```bash
   export DEV_SECRET_KEY="your-super-secret-key-here"
   ```

2. Keep this key **private** and **secure**. Never commit it to version control.

3. For production, use a strong, randomly generated key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

## Available Routes

All routes are prefixed with `/__dev__/` and require authentication via the secret key.

### 1. Developer Dashboard (HTML)
```
GET /__dev__/dashboard?key=YOUR_SECRET_KEY
```

**Description:** An interactive HTML dashboard showing:
- Database statistics
- System information
- Environment variables (sensitive data masked)
- Quick action links

**Usage:**
```bash
# Access in browser
https://your-app.com/__dev__/dashboard?key=YOUR_SECRET_KEY
```

### 2. Build Information (JSON)
```
GET /__dev__/info?key=YOUR_SECRET_KEY
```

**Description:** Returns comprehensive JSON with:
- System information (Python version, platform, etc.)
- Environment variables (masked sensitive data)
- Database statistics and table list
- Installed Python packages
- Flask configuration

**Usage:**
```bash
curl "https://your-app.com/__dev__/info?key=YOUR_SECRET_KEY"
```

### 3. File Structure (JSON)
```
GET /__dev__/structure?key=YOUR_SECRET_KEY
```

**Description:** Returns the project's file/directory structure (max 3 levels deep).

**Usage:**
```bash
curl "https://your-app.com/__dev__/structure?key=YOUR_SECRET_KEY"
```

### 4. All Routes (JSON)
```
GET /__dev__/routes?key=YOUR_SECRET_KEY
```

**Description:** Lists all registered Flask routes in the application.

**Usage:**
```bash
curl "https://your-app.com/__dev__/routes?key=YOUR_SECRET_KEY"
```

## 🔑 Authentication Methods

You can provide the secret key in two ways:

### 1. Query Parameter (recommended for browser)
```
?key=YOUR_SECRET_KEY
```

### 2. HTTP Header (recommended for API calls)
```
X-Dev-Key: YOUR_SECRET_KEY
```

Example with curl:
```bash
curl -H "X-Dev-Key: YOUR_SECRET_KEY" "https://your-app.com/__dev__/info"
```

## Security Notes

1. **404 on Invalid Key:** If an incorrect key is provided (or no key), the routes return a 404 error instead of 403. This hides the existence of these routes from unauthorized users.

2. **Masked Sensitive Data:** Environment variables containing passwords, secrets, keys, or tokens are automatically masked in responses.

3. **Production Safety:** 
   - Always use HTTPS in production
   - Rotate the DEV_SECRET_KEY periodically
   - Monitor access logs for unauthorized attempts
   - Consider IP whitelisting for additional security

4. **Access Control:** Only developers/admins who know the secret key can access these routes.

## Quick Start

1. Set your secret key:
   ```bash
   export DEV_SECRET_KEY="my-secret-dev-key-2024"
   ```

2. Start your application:
   ```bash
   python app.py
   ```

3. Access the dashboard in your browser:
   ```
   http://localhost:5000/__dev__/dashboard?key=my-secret-dev-key-2024
   ```

## Use Cases

- **Debugging:** Check environment variables and system configuration
- **Monitoring:** View database stats and health
- **Development:** Inspect file structure and registered routes
- **Troubleshooting:** Quick access to build information
- **Auditing:** Review installed packages and dependencies

## Extending

To add new developer routes, edit `/blueprints/dev.py`:

```python
@dev.route('/custom')
@require_dev_key
def custom_route():
    """Your custom developer route"""
    return jsonify({'message': 'Custom developer data'})
```

## Removing for Production

If you want to completely disable these routes in production:

1. Set an environment variable:
   ```bash
   export DISABLE_DEV_ROUTES=true
   ```

2. Modify `app.py` to conditionally register the blueprint:
   ```python
   # Developer Routes (Hidden - requires secret key)
   if not os.environ.get('DISABLE_DEV_ROUTES'):
       from blueprints.dev import dev
       app.register_blueprint(dev)
   ```

````