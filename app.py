import os
from web_control_panel import app

# Configure Flask to work in Replit environment  
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-this")

# Configure for Replit's proxy environment - allow all hosts
app.config.update(
    SERVER_NAME=None,
    APPLICATION_ROOT='/',
    PREFERRED_URL_SCHEME='https'
)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)