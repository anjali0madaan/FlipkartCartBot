import os
from werkzeug.middleware.proxy_fix import ProxyFix
from web_control_panel import app
from models import init_database

# Configure Flask to work in Replit environment  
app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    raise ValueError("SESSION_SECRET environment variable must be set")

# Configure database
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL environment variable must be set")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

# Initialize database tables
try:
    init_database()
    print("Database initialized successfully")
except Exception as e:
    print(f"Database initialization failed: {e}")

# Configure proxy fix for Replit's reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure for Replit's proxy environment - allow all hosts
app.config.update(
    SERVER_NAME=None,
    APPLICATION_ROOT='/',
    PREFERRED_URL_SCHEME='https'
)

if __name__ == '__main__':
    # Only enable debug mode in development
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)