#!/usr/bin/env python3
"""
Flipkart Automation Web Control Panel
Complete web-based interface for managing Flipkart automation sessions.
"""

from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import json
import os
import time
import logging
import subprocess
import sqlite3
import glob
from datetime import datetime
from session_persistence import FlipkartSessionManager
import threading
import queue
from typing import Dict, List, Optional

app = Flask(__name__)
CORS(app)

# Global error handlers to ensure JSON responses
@app.errorhandler(404)
def not_found_error(error):
    response = jsonify({
        'status': 'error',
        'message': 'Endpoint not found',
        'error_code': 404
    })
    response.headers['Content-Type'] = 'application/json'
    return response, 404

@app.errorhandler(500)
def internal_error(error):
    response = jsonify({
        'status': 'error',
        'message': 'Internal server error',
        'error_code': 500
    })
    response.headers['Content-Type'] = 'application/json'
    return response, 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions with JSON response."""
    response = jsonify({
        'status': 'error',
        'message': str(e),
        'error_code': 500
    })
    response.headers['Content-Type'] = 'application/json'
    return response, 500

# Global variables for managing session states
session_processes: Dict[str, subprocess.Popen] = {}
session_logs: Dict[str, queue.Queue] = {}
session_status: Dict[str, str] = {}  # 'running', 'stopped', 'finished', 'error'

# Global variables for sequential execution
sequential_execution_active = False
sequential_queue = queue.Queue()
sequential_thread = None
sequential_current_session = None

class WebControlPanel:
    def __init__(self):
        self.session_manager = FlipkartSessionManager()
        self.config_file = "config.json"
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging for web control panel."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_config(self) -> dict:
        """Load current configuration."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self.get_default_config()
    
    def save_config(self, config: dict) -> bool:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
            return False
    
    def get_default_config(self) -> dict:
        """Return default configuration."""
        return {
            "search_settings": {
                "product_name": "iPhone",
                "max_price": 999999,
                "min_price": 1,
                "search_query": "iPhone 14 128GB"
            },
            "automation_settings": {
                "wait_time": 3,
                "max_retries": 3,
                "headless_mode": True,
                "page_load_timeout": 30
            },
            "user_credentials": {
                "email": "",
                "password": ""
            },
            "sale_settings": {
                "enable_sale_detection": True,
                "min_discount_percentage": 10,
                "max_discount_percentage": 50,
                "prefer_sale_items": False
            },
            "filters": {
                "brand": "Apple",
                "sort_by": "price_low_to_high",
                "condition": "new"
            }
        }
    
    def get_all_sessions(self) -> List[dict]:
        """Get all available sessions with status."""
        try:
            sessions = self.session_manager.list_available_sessions()
            result = []
            
            for session in sessions:
                try:
                    # Safely extract session data with defaults
                    session_id = session.get('user', 'unknown')
                    status = session_status.get(session_id, 'stopped')
                    
                    result.append({
                        'id': session_id,
                        'user': session.get('user', 'unknown'),
                        'created': session.get('created', 'Unknown'),
                        'last_used': session.get('last_used', 'Unknown'),
                        'valid': session.get('valid', False),
                        'status': status,
                        'profile_name': session.get('profile_name', ''),
                        'can_start': session.get('valid', False) and status not in ['running'],
                        'can_stop': status == 'running'
                    })
                except Exception as e:
                    self.logger.error(f"Error processing session {session}: {e}")
                    # Add a safe fallback entry for malformed sessions
                    result.append({
                        'id': f"error-{len(result)}",
                        'user': 'Error loading session',
                        'created': 'Unknown',
                        'last_used': 'Unknown',
                        'valid': False,
                        'status': 'error',
                        'profile_name': '',
                        'can_start': False,
                        'can_stop': False
                    })
            
            return result
        except Exception as e:
            self.logger.error(f"Error getting sessions: {e}")
            return []

def validate_flipkart_login(profile_dir: str, session_id: str) -> bool:
    """
    Validate if user has successfully logged into Flipkart by checking cookies in profile directory.
    Returns True if valid Flipkart login cookies are found.
    """
    try:
        # Look for Chrome cookies database in the profile directory
        cookies_db_path = os.path.join(profile_dir, "Default", "Cookies")
        
        if not os.path.exists(cookies_db_path):
            print(f"Cookies database not found at: {cookies_db_path}")
            return False
        
        # Connect to Chrome's cookies database
        conn = sqlite3.connect(cookies_db_path)
        cursor = conn.cursor()
        
        # Check for Flipkart login-related cookies
        login_cookies = [
            'at',           # auth token
            'uc',           # user context
            'userUdid',     # user unique device ID
            'SN',           # session number
            'T',            # token
        ]
        
        flipkart_cookies_found = []
        
        for cookie_name in login_cookies:
            cursor.execute("""
                SELECT name, value, host_key 
                FROM cookies 
                WHERE host_key LIKE '%flipkart.com%' 
                AND name = ?
            """, (cookie_name,))
            
            results = cursor.fetchall()
            if results:
                flipkart_cookies_found.extend(results)
                print(f"Found {cookie_name} cookie for Flipkart")
        
        # Also check for any cookies from flipkart.com domain
        cursor.execute("""
            SELECT COUNT(*) 
            FROM cookies 
            WHERE host_key LIKE '%flipkart.com%'
        """)
        
        flipkart_cookie_count = cursor.fetchone()[0]
        conn.close()
        
        # Consider login valid if we have login cookies OR sufficient flipkart cookies
        is_valid = len(flipkart_cookies_found) >= 2 or flipkart_cookie_count >= 5
        
        print(f"Login validation for session {session_id}:")
        print(f"  - Login cookies found: {len(flipkart_cookies_found)}")
        print(f"  - Total Flipkart cookies: {flipkart_cookie_count}")
        print(f"  - Validation result: {'VALID' if is_valid else 'INVALID'}")
        
        return is_valid
        
    except Exception as e:
        print(f"Error validating login for session {session_id}: {e}")
        return False


def sequential_worker():
    """Worker function that processes sessions sequentially."""
    global sequential_execution_active, sequential_current_session
    
    while sequential_execution_active:
        try:
            # Get next session from queue (blocking call with timeout)
            session_data = sequential_queue.get(timeout=1.0)
            if session_data is None:  # Poison pill to stop worker
                break
                
            session_id = session_data['id']
            sequential_current_session = session_id
            
            # Start the session
            cmd = ["python", "run_automation.py", "--use-session", session_id, "--yes"]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            session_processes[session_id] = process
            session_status[session_id] = 'running'
            
            # Initialize log queue
            if session_id not in session_logs:
                session_logs[session_id] = queue.Queue()
            
            # Start log monitoring
            log_thread = threading.Thread(
                target=monitor_session_logs,
                args=(session_id, process),
                daemon=True
            )
            log_thread.start()
            
            # Wait for this session to complete before starting next one
            process.wait()
            
            # Update status based on return code
            if process.returncode == 0:
                session_status[session_id] = 'finished'
            else:
                session_status[session_id] = 'error'
            
            # Remove from active processes
            if session_id in session_processes:
                del session_processes[session_id]
                
            sequential_queue.task_done()
            
        except queue.Empty:
            # Timeout waiting for next session, continue loop
            continue
        except Exception as e:
            # Check if session_id is defined before using it
            if 'session_id' in locals():
                session_status[session_id] = 'error'
                if session_id in session_processes:
                    del session_processes[session_id]
            print(f"Error in sequential worker: {e}")
            if not sequential_queue.empty():
                sequential_queue.task_done()
    
    sequential_current_session = None
    print("Sequential worker stopped")


control_panel = WebControlPanel()

@app.route('/')
def index():
    """Main control panel interface."""
    timestamp = int(time.time())
    return render_template('index.html', timestamp=timestamp)

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get all available sessions with their status."""
    try:
        sessions = control_panel.get_all_sessions()
        response = jsonify({
            'status': 'success',
            'sessions': sessions,
            'total_sessions': len(sessions),
            'timestamp': datetime.now().isoformat()
        })
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        control_panel.logger.error(f"Error in /api/sessions: {e}")
        response = jsonify({
            'status': 'error',
            'message': str(e)
        })
        response.headers['Content-Type'] = 'application/json'
        return response, 500

@app.route('/api/sessions/<session_id>/start', methods=['POST'])
def start_session(session_id):
    """Start a specific session."""
    try:
        # Check if session already running
        if session_id in session_processes and session_processes[session_id].poll() is None:
            response = jsonify({
                'status': 'error',
                'message': f'Session {session_id} is already running'
            })
            response.headers['Content-Type'] = 'application/json'
            return response, 400
        
        # Start the automation process
        cmd = ["python", "run_automation.py", "--use-session", session_id, "--yes"]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        session_processes[session_id] = process
        session_status[session_id] = 'running'
        
        # Initialize log queue for this session
        if session_id not in session_logs:
            session_logs[session_id] = queue.Queue()
        
        # Start log monitoring thread
        log_thread = threading.Thread(
            target=monitor_session_logs,
            args=(session_id, process),
            daemon=True
        )
        log_thread.start()
        
        response = jsonify({
            'status': 'success',
            'message': f'Session {session_id} started successfully',
            'session_id': session_id,
            'pid': process.pid
        })
        response.headers['Content-Type'] = 'application/json'
        return response
    
    except Exception as e:
        # Ensure session_id is properly handled in error cases
        if 'session_id' in locals():
            session_status[session_id] = 'error'
            error_message = f'Failed to start session {session_id}: {str(e)}'
        else:
            error_message = f'Failed to start session: {str(e)}'
        
        response = jsonify({
            'status': 'error',
            'message': error_message
        })
        response.headers['Content-Type'] = 'application/json'
        return response, 500

@app.route('/api/sessions/<session_id>/stop', methods=['POST'])
def stop_session(session_id):
    """Stop a specific session."""
    try:
        if session_id in session_processes:
            process = session_processes[session_id]
            if process.poll() is None:  # Process is still running
                process.terminate()
                process.wait(timeout=10)  # Wait up to 10 seconds
                
            del session_processes[session_id]
        
        session_status[session_id] = 'stopped'
        
        response = jsonify({
            'status': 'success',
            'message': f'Session {session_id} stopped successfully'
        })
        response.headers['Content-Type'] = 'application/json'
        return response
    
    except Exception as e:
        response = jsonify({
            'status': 'error',
            'message': f'Failed to stop session {session_id}: {str(e)}'
        })
        response.headers['Content-Type'] = 'application/json'
        return response, 500

@app.route('/api/sessions/start-all', methods=['POST'])
def start_all_sessions():
    """Start all valid sessions simultaneously."""
    try:
        sessions = control_panel.get_all_sessions()
        started_sessions = []
        failed_sessions = []
        
        for session in sessions:
            if session['can_start']:
                try:
                    # Use the start_session logic
                    session_id = session['id']
                    cmd = ["python", "run_automation.py", "--use-session", session_id, "--yes"]
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1
                    )
                    
                    session_processes[session_id] = process
                    session_status[session_id] = 'running'
                    
                    # Initialize log queue
                    if session_id not in session_logs:
                        session_logs[session_id] = queue.Queue()
                    
                    # Start log monitoring
                    log_thread = threading.Thread(
                        target=monitor_session_logs,
                        args=(session_id, process),
                        daemon=True
                    )
                    log_thread.start()
                    
                    started_sessions.append(session_id)
                    
                except Exception as e:
                    # Ensure session_id is available before using it
                    if 'session_id' in locals():
                        failed_sessions.append({'session': session_id, 'error': str(e)})
                        session_status[session_id] = 'error'
                    else:
                        failed_sessions.append({'session': 'unknown', 'error': str(e)})
        
        return jsonify({
            'status': 'success',
            'message': f'Started {len(started_sessions)} sessions',
            'started_sessions': started_sessions,
            'failed_sessions': failed_sessions,
            'total_attempted': len([s for s in sessions if s['can_start']])
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to start all sessions: {str(e)}'
        }), 500

@app.route('/api/sessions/start-sequential', methods=['POST'])
def start_all_sessions_sequential():
    """Start all valid sessions sequentially (one after another)."""
    global sequential_execution_active, sequential_thread
    
    try:
        # Check if sequential execution is already running
        if sequential_execution_active:
            return jsonify({
                'status': 'error',
                'message': 'Sequential execution is already running'
            }), 400
        
        sessions = control_panel.get_all_sessions()
        startable_sessions = [s for s in sessions if s['can_start']]
        
        if not startable_sessions:
            return jsonify({
                'status': 'error',
                'message': 'No valid sessions available to start'
            }), 400
        
        # Clear the queue and add all startable sessions
        while not sequential_queue.empty():
            try:
                sequential_queue.get_nowait()
            except queue.Empty:
                break
        
        for session in startable_sessions:
            sequential_queue.put(session)
        
        # Start sequential execution
        sequential_execution_active = True
        sequential_thread = threading.Thread(
            target=sequential_worker,
            daemon=True
        )
        sequential_thread.start()
        
        return jsonify({
            'status': 'success',
            'message': f'Sequential execution started for {len(startable_sessions)} sessions',
            'total_sessions': len(startable_sessions),
            'sessions': [s['id'] for s in startable_sessions],
            'mode': 'sequential'
        })
    
    except Exception as e:
        sequential_execution_active = False
        return jsonify({
            'status': 'error',
            'message': f'Failed to start sequential execution: {str(e)}'
        }), 500

@app.route('/api/sessions/stop-all', methods=['POST'])
def stop_all_sessions():
    """Stop all running sessions and sequential execution."""
    global sequential_execution_active
    
    try:
        stopped_sessions = []
        failed_sessions = []
        
        # Stop sequential execution if running
        sequential_stopped = False
        if sequential_execution_active:
            sequential_execution_active = False
            # Add poison pill to queue to stop worker
            sequential_queue.put(None)
            sequential_stopped = True
        
        # Stop all individual running sessions
        for session_id, process in list(session_processes.items()):
            try:
                if process.poll() is None:  # Process is still running
                    process.terminate()
                    process.wait(timeout=10)
                    
                stopped_sessions.append(session_id)
                session_status[session_id] = 'stopped'
                
            except Exception as e:
                failed_sessions.append({'session': session_id, 'error': str(e)})
        
        # Clear all processes
        session_processes.clear()
        
        message = f'Stopped {len(stopped_sessions)} sessions'
        if sequential_stopped:
            message += ' and sequential execution'
        
        return jsonify({
            'status': 'success',
            'message': message,
            'stopped_sessions': stopped_sessions,
            'failed_sessions': failed_sessions,
            'sequential_stopped': sequential_stopped
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to stop all sessions: {str(e)}'
        }), 500

@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    """Get or update automation configuration."""
    if request.method == 'GET':
        config = control_panel.load_config()
        return jsonify({
            'status': 'success',
            'config': config
        })
    
    elif request.method == 'POST':
        try:
            new_config = request.get_json()
            if not new_config:
                return jsonify({
                    'status': 'error',
                    'message': 'No configuration data provided'
                }), 400
            
            # Validate and save configuration
            if control_panel.save_config(new_config):
                return jsonify({
                    'status': 'success',
                    'message': 'Configuration updated successfully',
                    'config': new_config
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to save configuration'
                }), 500
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to update configuration: {str(e)}'
            }), 500

@app.route('/api/logs/<session_id>', methods=['GET'])
def get_session_logs(session_id):
    """Get logs for a specific session."""
    try:
        # Get recent logs from queue
        logs = []
        
        if session_id in session_logs:
            log_queue = session_logs[session_id]
            
            # Get all available logs (up to last 100 entries)
            temp_logs = []
            try:
                while not log_queue.empty() and len(temp_logs) < 100:
                    temp_logs.append(log_queue.get_nowait())
            except queue.Empty:
                pass
            
            # Put logs back in queue (keep last 50 for future requests)
            for log in temp_logs[-50:]:
                log_queue.put(log)
            
            logs = temp_logs
        
        # Also check for log files
        log_file = f"flipkart_automation.log"
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    file_logs = f.readlines()[-50:]  # Get last 50 lines
                    logs.extend([line.strip() for line in file_logs if line.strip()])
            except Exception:
                pass
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'logs': logs[-100:],  # Return last 100 log entries
            'session_status': session_status.get(session_id, 'unknown'),
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get logs for session {session_id}: {str(e)}'
        }), 500

@app.route('/api/logs/<session_id>/stream')
def stream_logs(session_id):
    """Stream logs for a session in real-time."""
    def generate():
        """Generate log stream."""
        last_check = time.time()
        
        while True:
            if session_id in session_logs:
                log_queue = session_logs[session_id]
                logs = []
                
                try:
                    while not log_queue.empty():
                        logs.append(log_queue.get_nowait())
                except queue.Empty:
                    pass
                
                if logs:
                    for log in logs:
                        yield f"data: {json.dumps({'log': log, 'timestamp': time.time()})}\n\n"
            
            # Send heartbeat every 5 seconds
            if time.time() - last_check > 5:
                yield f"data: {json.dumps({'heartbeat': True, 'timestamp': time.time()})}\n\n"
                last_check = time.time()
            
            time.sleep(1)
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
    )

def monitor_session_logs(session_id: str, process: subprocess.Popen):
    """Monitor logs from a session process."""
    try:
        if process.stdout is None:
            session_status[session_id] = 'error'
            return
        
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            
            # Add to log queue
            if session_id in session_logs:
                try:
                    # Keep queue size manageable
                    if session_logs[session_id].qsize() > 200:
                        try:
                            session_logs[session_id].get_nowait()
                        except queue.Empty:
                            pass
                    
                    session_logs[session_id].put({
                        'timestamp': datetime.now().isoformat(),
                        'message': line.strip(),
                        'session_id': session_id
                    })
                except Exception:
                    pass
        
        # Process finished
        process.wait()
        session_status[session_id] = 'finished' if process.returncode == 0 else 'error'
        
        # Clean up
        if session_id in session_processes:
            del session_processes[session_id]
            
    except Exception as e:
        session_status[session_id] = 'error'
        if session_id in session_logs:
            session_logs[session_id].put({
                'timestamp': datetime.now().isoformat(),
                'message': f'Error monitoring logs: {str(e)}',
                'session_id': session_id
            })

@app.route('/api/vnc/auth', methods=['GET'])
def get_vnc_auth():
    """Get VNC authentication credentials for embedded noVNC."""
    try:
        # Get VNC password from environment
        vnc_password = os.environ.get('VNC_PASSWORD')
        if not vnc_password:
            return jsonify({
                'status': 'error',
                'message': 'VNC password not configured'
            }), 500
        
        # Get the current host from request
        host = request.host.split(':')[0]
        
        response = jsonify({
            'status': 'success',
            'credentials': {
                'username': 'runner',
                'password': vnc_password,
                'host': host,
                'port': 5900,
                'websocket_port': 6080
            },
            'connection_info': {
                'vnc_url': f'ws://{host}:6080/websockify',
                'web_url': f'http://{host}:6080/vnc.html'
            }
        })
        response.headers['Content-Type'] = 'application/json'
        return response
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get VNC credentials: {str(e)}'
        }), 500

@app.route('/api/sessions/create', methods=['POST'])
def create_new_session():
    """Create a new Flipkart session with guided setup."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        user_identifier = data.get('user_identifier', '').strip()
        if not user_identifier:
            return jsonify({
                'status': 'error',
                'message': 'User identifier (email/mobile) is required'
            }), 400
        
        # Check if session already exists
        existing_sessions = control_panel.get_all_sessions()
        for session in existing_sessions:
            if session.get('user') == user_identifier:
                return jsonify({
                    'status': 'error',
                    'message': f'Session for {user_identifier} already exists'
                }), 400
        
        # Create session identifier
        safe_identifier = user_identifier.replace('@', '_').replace('+', '_').replace(' ', '_')
        session_id = safe_identifier
        
        # Initialize session status
        session_status[session_id] = 'creating'
        
        # Start session creation process in background
        creation_thread = threading.Thread(
            target=create_session_background,
            args=(session_id, user_identifier),
            daemon=True
        )
        creation_thread.start()
        
        return jsonify({
            'status': 'success',
            'message': 'Session creation started',
            'session_id': session_id,
            'user_identifier': user_identifier,
            'next_step': 'vnc_login'
        })
    
    except Exception as e:
        control_panel.logger.error(f"Error creating session: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to create session: {str(e)}'
        }), 500

def create_session_background(session_id: str, user_identifier: str):
    """Background task to handle session creation."""
    try:
        control_panel.logger.info(f"Starting background session creation for {session_id}")
        
        # Update status
        session_status[session_id] = 'creating_profile'
        
        # Initialize log queue for this session creation
        if session_id not in session_logs:
            session_logs[session_id] = queue.Queue()
        
        # Add creation log
        session_logs[session_id].put({
            'timestamp': datetime.now().isoformat(),
            'message': f'Session creation started for {user_identifier}',
            'session_id': session_id
        })
        
        # Create profile directory for this session
        profile_dir = os.path.join(control_panel.session_manager.base_profile_dir, f"profile_{session_id}")
        os.makedirs(profile_dir, exist_ok=True)
        
        session_logs[session_id].put({
            'timestamp': datetime.now().isoformat(),
            'message': f'Profile directory created: {profile_dir}',
            'session_id': session_id
        })
        
        # Update status
        session_status[session_id] = 'launching_chrome'
        
        # Launch Chrome in VNC desktop with the specific profile directory
        try:
            # Build Chrome command with profile directory
            chrome_cmd = [
                'chromium-browser',
                f'--user-data-dir={profile_dir}',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--window-size=1920,1080',
                '--start-maximized',
                'https://www.flipkart.com/account/login'
            ]
            
            # Set environment to use VNC display
            env = os.environ.copy()
            env['DISPLAY'] = ':0'
            
            session_logs[session_id].put({
                'timestamp': datetime.now().isoformat(),
                'message': f'Launching Chrome in VNC for profile {session_id}...',
                'session_id': session_id
            })
            
            # Launch Chrome in VNC desktop
            chrome_process = subprocess.Popen(
                chrome_cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            session_logs[session_id].put({
                'timestamp': datetime.now().isoformat(),
                'message': f'Chrome launched successfully in VNC (PID: {chrome_process.pid})',
                'session_id': session_id
            })
            
            session_logs[session_id].put({
                'timestamp': datetime.now().isoformat(),
                'message': 'Chrome is now running in VNC with Flipkart login page. Complete your login.',
                'session_id': session_id
            })
            
            # Update status to awaiting login
            session_status[session_id] = 'awaiting_login'
            
            control_panel.logger.info(f"Chrome launched for session {session_id} in VNC desktop")
            
        except Exception as chrome_error:
            session_logs[session_id].put({
                'timestamp': datetime.now().isoformat(),
                'message': f'Failed to launch Chrome: {str(chrome_error)}',
                'session_id': session_id
            })
            session_status[session_id] = 'error'
            raise chrome_error
        
    except Exception as e:
        control_panel.logger.error(f"Error in background session creation: {e}")
        session_status[session_id] = 'error'
        if session_id in session_logs:
            session_logs[session_id].put({
                'timestamp': datetime.now().isoformat(),
                'message': f'Error creating session: {str(e)}',
                'session_id': session_id
            })

@app.route('/api/sessions/<session_id>/finalize', methods=['POST'])
def finalize_session_creation(session_id):
    """Finalize session creation after VNC login completion."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        user_identifier = data.get('user_identifier', '')
        login_completed = data.get('login_completed', False)
        
        if not login_completed:
            return jsonify({
                'status': 'error',
                'message': 'Login not completed'
            }), 400
        
        # Use session manager to finalize the session
        try:
            # Validate login by checking cookies in profile directory
            profile_dir = os.path.join(control_panel.session_manager.base_profile_dir, f"profile_{session_id}")
            
            if session_id in session_logs:
                session_logs[session_id].put({
                    'timestamp': datetime.now().isoformat(),
                    'message': f'Validating login in profile directory: {profile_dir}',
                    'session_id': session_id
                })
            
            # Check if profile directory exists
            if not os.path.exists(profile_dir):
                session_status[session_id] = 'error'
                return jsonify({
                    'status': 'error',
                    'message': f'Profile directory not found: {profile_dir}. Please complete login in VNC.'
                }), 400
            
            # Validate login by checking for Flipkart cookies
            login_valid = validate_flipkart_login(profile_dir, session_id)
            
            if not login_valid:
                session_status[session_id] = 'error'
                if session_id in session_logs:
                    session_logs[session_id].put({
                        'timestamp': datetime.now().isoformat(),
                        'message': 'Login validation failed - no valid Flipkart cookies found',
                        'session_id': session_id
                    })
                return jsonify({
                    'status': 'error',
                    'message': 'Login validation failed. Please complete login in VNC and try again.'
                }), 400
            
            # Create the session using the session manager's logic
            session_manager = control_panel.session_manager
            
            # Update session records with proper profile path
            sessions = session_manager.load_sessions()
            sessions[user_identifier] = {
                'user': user_identifier,
                'created': datetime.now().isoformat(),
                'last_used': datetime.now().isoformat(),
                'valid': True,
                'profile_name': f"profile_{session_id}",
                'profile_path': profile_dir,
                'session_id': session_id
            }
            session_manager.save_sessions(sessions)
            
            # Update status
            session_status[session_id] = 'ready'
            
            # Add success log
            if session_id in session_logs:
                session_logs[session_id].put({
                    'timestamp': datetime.now().isoformat(),
                    'message': f'Session {session_id} created and validated successfully',
                    'session_id': session_id
                })
            
            return jsonify({
                'status': 'success',
                'message': f'Session {session_id} created and validated successfully',
                'session_id': session_id,
                'user_identifier': user_identifier
            })
        
        except Exception as e:
            session_status[session_id] = 'error'
            return jsonify({
                'status': 'error',
                'message': f'Failed to finalize session: {str(e)}'
            }), 500
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to finalize session creation: {str(e)}'
        }), 500

# Health check endpoint
@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    response = jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_sessions': len([s for s in session_status.values() if s == 'running']),
        'total_sessions': len(session_status)
    })
    response.headers['Content-Type'] = 'application/json'
    return response

if __name__ == '__main__':
    # Ensure templates directory exists
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("🌐 Starting Flipkart Automation Web Control Panel...")
    print("📊 Control Panel will be available at: http://localhost:5000")
    print("🔧 API endpoints available at: http://localhost:5000/api/")
    print()
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )