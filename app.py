import os
from werkzeug.middleware.proxy_fix import ProxyFix
from web_control_panel import app

# Configure Flask to work in Replit environment  
app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    raise ValueError("SESSION_SECRET environment variable must be set")

# Configure proxy fix for Replit's reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure for Replit's proxy environment - allow all hosts
app.config.update(
    SERVER_NAME=None,
    APPLICATION_ROOT='/',
    PREFERRED_URL_SCHEME='https'
)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)