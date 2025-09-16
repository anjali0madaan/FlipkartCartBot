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
from datetime import datetime
from session_persistence import FlipkartSessionManager
import threading
import queue
from typing import Dict, List, Optional

app = Flask(__name__)
CORS(app)

# Global variables for managing session states
session_processes: Dict[str, subprocess.Popen] = {}
session_logs: Dict[str, queue.Queue] = {}
session_status: Dict[str, str] = {}  # 'running', 'stopped', 'finished', 'error'

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
        sessions = self.session_manager.list_available_sessions()
        result = []
        
        for session in sessions:
            session_id = session['user']
            status = session_status.get(session_id, 'stopped')
            
            result.append({
                'id': session_id,
                'user': session['user'],
                'created': session['created'],
                'last_used': session['last_used'],
                'valid': session['valid'],
                'status': status,
                'profile_name': session.get('profile_name', ''),
                'can_start': session['valid'] and status not in ['running'],
                'can_stop': status == 'running'
            })
        
        return result

control_panel = WebControlPanel()

@app.route('/')
def index():
    """Main control panel interface."""
    return render_template('index.html')

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get all available sessions with their status."""
    try:
        sessions = control_panel.get_all_sessions()
        return jsonify({
            'status': 'success',
            'sessions': sessions,
            'total_sessions': len(sessions),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/sessions/<session_id>/start', methods=['POST'])
def start_session(session_id):
    """Start a specific session."""
    try:
        # Check if session already running
        if session_id in session_processes and session_processes[session_id].poll() is None:
            return jsonify({
                'status': 'error',
                'message': f'Session {session_id} is already running'
            }), 400
        
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
        
        return jsonify({
            'status': 'success',
            'message': f'Session {session_id} started successfully',
            'session_id': session_id,
            'pid': process.pid
        })
    
    except Exception as e:
        session_status[session_id] = 'error'
        return jsonify({
            'status': 'error',
            'message': f'Failed to start session {session_id}: {str(e)}'
        }), 500

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
        
        return jsonify({
            'status': 'success',
            'message': f'Session {session_id} stopped successfully'
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to stop session {session_id}: {str(e)}'
        }), 500

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
                    failed_sessions.append({'session': session_id, 'error': str(e)})
                    session_status[session_id] = 'error'
        
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

@app.route('/api/sessions/stop-all', methods=['POST'])
def stop_all_sessions():
    """Stop all running sessions."""
    try:
        stopped_sessions = []
        failed_sessions = []
        
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
        
        return jsonify({
            'status': 'success',
            'message': f'Stopped {len(stopped_sessions)} sessions',
            'stopped_sessions': stopped_sessions,
            'failed_sessions': failed_sessions
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

# Health check endpoint
@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_sessions': len([s for s in session_status.values() if s == 'running']),
        'total_sessions': len(session_status)
    })

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