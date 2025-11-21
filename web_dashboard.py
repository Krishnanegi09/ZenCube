#!/usr/bin/env python3
"""
ZenCube Web Dashboard
Flask-based web interface with real-time monitoring
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit
import subprocess
import threading
import os
import json
import time
import platform
import psutil
import tempfile
import shutil
import uuid
import shlex
from pathlib import Path

# Import code_analyzer with error handling
try:
    from code_analyzer import CodeAnalyzer
except ImportError as e:
    print(f"Warning: Could not import CodeAnalyzer: {e}")
    # Create a minimal fallback analyzer
    class CodeAnalyzer:
        def analyze_file(self, file_path):
            return {
                'error': 'Code analysis unavailable',
                'total_issues': 0,
                'critical': 0,
                'high': 0,
                'medium': 0,
                'vulnerabilities': [],
                'warnings': []
            }

# Import platform utilities with error handling for Vercel
try:
    from platform_utils import (
        IS_WINDOWS, IS_MACOS, IS_UNIX,
        find_sandbox as platform_find_sandbox,
        remove_quarantine_if_needed as platform_remove_quarantine,
        get_executable_extension,
        make_executable
    )
except ImportError:
    # Fallback if platform_utils is not available (shouldn't happen, but safe)
    import platform
    IS_WINDOWS = platform.system() == "Windows"
    IS_MACOS = platform.system() == "Darwin"
    IS_UNIX = os.name != "nt"
    
    def platform_find_sandbox():
        script_dir = os.path.dirname(os.path.abspath(__file__))
        paths = [
            os.path.join(script_dir, "sandbox"),
            os.path.join(script_dir, "sandbox.exe"),
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return None
    
    def platform_remove_quarantine_if_needed(file_path):
        pass  # No-op
    
    def get_executable_extension():
        return ".exe" if IS_WINDOWS else ""
    
    def make_executable(file_path):
        if IS_UNIX:
            os.chmod(file_path, 0o755)

# Initialize Flask app with error handling
try:
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'zencube-secret-key-2025')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
except Exception as e:
    print(f"Error initializing Flask app: {e}")
    raise
# Configure SocketIO for Vercel compatibility (use polling as fallback)
# On Vercel serverless, SocketIO may have limited functionality
try:
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*", 
        async_mode='threading',
        allow_upgrades=True,
        transports=['polling', 'websocket'],
        logger=not os.environ.get('VERCEL'),
        engineio_logger=not os.environ.get('VERCEL')
    )
except Exception as e:
    print(f"Warning: SocketIO initialization issue: {e}")
    # Fallback for serverless environments
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*",
        async_mode='threading',
        logger=False,
        engineio_logger=False
    )

# Global state
running_processes = {}
monitoring_threads = {}
# Use /tmp on Vercel (serverless environment), otherwise use 'uploads'
# On Vercel, /tmp is the only writable directory
try:
    if os.environ.get('VERCEL'):
        UPLOAD_DIR = Path('/tmp/zencube_uploads')
    else:
        UPLOAD_DIR = Path('uploads')
except Exception as e:
    print(f"Warning: Could not set UPLOAD_DIR: {e}")
    UPLOAD_DIR = Path('/tmp' if os.environ.get('VERCEL') else 'uploads')


def ensure_upload_dir():
    """Ensure the uploads directory exists"""
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # On Vercel, /tmp might not allow directory creation, use tempfile instead
        if os.environ.get('VERCEL'):
            print(f"Warning: Could not create upload dir: {e}")


def is_within_uploads(path: Path) -> bool:
    """Check if a path is inside the uploads directory"""
    try:
        return UPLOAD_DIR.resolve() in path.resolve().parents or path.resolve() == UPLOAD_DIR.resolve()
    except FileNotFoundError:
        return False


def save_uploaded_file(file_storage):
    """Persist an uploaded file and return its path"""
    ensure_upload_dir()
    original_name = secure_filename(file_storage.filename) or f"upload_{uuid.uuid4().hex}"
    suffix = Path(original_name).suffix
    unique_name = f"{Path(original_name).stem}_{uuid.uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / unique_name
    file_storage.save(destination)
    return destination


def cleanup_process_resources(process_id):
    """Remove uploaded/temporary files linked to a process"""
    info = running_processes.pop(process_id, None)
    if not info:
        return

    cleanup_paths = info.get('cleanup_paths', [])
    uploaded_file = info.get('uploaded_file')

    paths_to_remove = []
    if uploaded_file:
        uploaded_path = Path(uploaded_file)
        if is_within_uploads(uploaded_path):
            paths_to_remove.append(uploaded_path)

    for p in cleanup_paths:
        path_obj = Path(p)
        if is_within_uploads(path_obj):
            paths_to_remove.append(path_obj)

    for path in paths_to_remove:
        try:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink(missing_ok=True)
        except Exception:
            # Suppress cleanup errors
            pass


def build_execution_command(file_path: Path):
    """Determine how to execute a file and return command parts + cleanup paths"""
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    cleanup_paths = []
    ext = file_path.suffix.lower()

    interpreter_map = {
        '.py': ['python3'] if IS_UNIX else ['python'],
        '.sh': ['bash'],
        '.js': ['node'],
        '.rb': ['ruby'],
        '.pl': ['perl'],
        '.ps1': ['pwsh'] if IS_UNIX else ['powershell'],
        '.bat': ['cmd.exe', '/c'] if IS_WINDOWS else None,
    }

    # Allow executables
    if os.access(file_path, os.X_OK) and ext not in interpreter_map:
        return [str(file_path)], cleanup_paths

    if ext in interpreter_map and interpreter_map[ext]:
        interpreter_cmd = interpreter_map[ext]
        if shutil.which(interpreter_cmd[0]) is None:
            raise RuntimeError(f"Required interpreter '{interpreter_cmd[0]}' not found on PATH.")
        return interpreter_cmd + [str(file_path)], cleanup_paths

        if ext in ('.c',):
        ensure_upload_dir()
        build_dir = UPLOAD_DIR / f"build_{uuid.uuid4().hex}"
        build_dir.mkdir(parents=True, exist_ok=True)
        output_name = file_path.stem + get_executable_extension()
        output_path = build_dir / output_name
        compile_cmd = ['gcc', str(file_path), '-o', str(output_path)]
        result = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"C compilation failed:\n{result.stderr or result.stdout}")
        make_executable(str(output_path))
        cleanup_paths.append(str(build_dir))
        return [str(output_path)], cleanup_paths

        if ext in ('.cpp', '.cc', '.cxx'):
        ensure_upload_dir()
        build_dir = UPLOAD_DIR / f"build_{uuid.uuid4().hex}"
        build_dir.mkdir(parents=True, exist_ok=True)
        output_name = file_path.stem + get_executable_extension()
        output_path = build_dir / output_name
        compile_cmd = ['g++', str(file_path), '-o', str(output_path)]
        result = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"C++ compilation failed:\n{result.stderr or result.stdout}")
        make_executable(str(output_path))
        cleanup_paths.append(str(build_dir))
        return [str(output_path)], cleanup_paths

    if ext == '.java':
        ensure_upload_dir()
        build_dir = UPLOAD_DIR / f"build_{uuid.uuid4().hex}"
        build_dir.mkdir(parents=True, exist_ok=True)
        compile_cmd = ['javac', '-d', str(build_dir), str(file_path)]
        result = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"Java compilation failed:\n{result.stderr or result.stdout}")
        package_name = None
        try:
            with file_path.open('r', encoding='utf-8', errors='ignore') as src:
                for line in src:
                    stripped = line.strip()
                    if stripped.startswith('package '):
                        package_name = stripped.split('package', 1)[1].strip().rstrip(';')
                        break
        except Exception:
            package_name = None

        class_name = file_path.stem
        fqcn = f"{package_name}.{class_name}" if package_name else class_name
        cleanup_paths.append(str(build_dir))
        return ['java', '-cp', str(build_dir), fqcn], cleanup_paths

    raise ValueError(f"Unsupported file type: {file_path.suffix}")


def launch_sandbox_process(command_parts, limits, metadata):
    """Launch sandbox with computed command parts"""
    sandbox_path = find_sandbox()
    if not sandbox_path:
        raise RuntimeError('Sandbox executable not found')

    full_cmd = [sandbox_path]

    cpu = limits.get('cpu')
    memory = limits.get('memory')
    processes = limits.get('processes')
    file_size = limits.get('file_size')

    if cpu:
        full_cmd.append(f"--cpu={cpu}")
    if memory:
        full_cmd.append(f"--mem={memory}")
    if processes:
        full_cmd.append(f"--procs={processes}")
    if file_size:
        full_cmd.append(f"--fsize={file_size}")

    full_cmd.extend(command_parts)

    process_id = f"proc_{uuid.uuid4().hex}"

    proc = subprocess.Popen(
        full_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    running_processes[process_id] = {
        'process': proc,
        'pid': proc.pid,
        'command': ' '.join(full_cmd),
        'start_time': time.time(),
        'stdin': proc.stdin,
        'uploaded_file': metadata.get('uploaded_file'),
        'cleanup_paths': metadata.get('cleanup_paths', [])
    }

    # Start monitoring thread
    monitor_thread = threading.Thread(
        target=monitor_process,
        args=(proc.pid, process_id),
        daemon=True
    )
    monitoring_threads[process_id] = monitor_thread
    monitor_thread.start()

    # Start streaming output
    output_thread = threading.Thread(
        target=stream_process_output,
        args=(proc, process_id),
        daemon=True
    )
    output_thread.start()

    return process_id, proc.pid

def find_sandbox():
    """Find sandbox executable - uses universal platform detection"""
    sandbox_path = platform_find_sandbox()
    if sandbox_path:
        platform_remove_quarantine(sandbox_path)
    return sandbox_path

def monitor_process(pid, process_id):
    """Monitor a process and send updates via WebSocket"""
    try:
        proc = psutil.Process(pid)
        start_time = time.time()
        
        while proc.is_running() and process_id in running_processes:
            try:
                cpu_percent = proc.cpu_percent(interval=0.1)
                memory_info = proc.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                # Use vms instead of vss - vms is available on macOS/Linux, vss is not standard
                # On Windows, use rss as fallback
                virtual_mb = getattr(memory_info, 'vms', memory_info.rss) / 1024 / 1024
                num_threads = proc.num_threads()
                num_fds = len(proc.open_files()) if hasattr(proc, 'open_files') else 0
                
                elapsed = time.time() - start_time
                
                stats = {
                    'process_id': process_id,
                    'cpu_percent': round(cpu_percent, 2),
                    'memory_mb': round(memory_mb, 2),
                    'virtual_memory_mb': round(virtual_mb, 2),
                    'threads': num_threads,
                    'file_descriptors': num_fds,
                    'elapsed_time': round(elapsed, 2),
                    'timestamp': time.time()
                }
                
                try:
                    socketio.emit('resource_update', stats)
                except Exception:
                    pass  # SocketIO may not work in serverless, continue silently
                time.sleep(0.5)  # Update every 500ms
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
                
    except Exception as e:
        try:
            socketio.emit('error', {'message': f'Monitoring error: {str(e)}'})
        except Exception:
            pass  # SocketIO may not work in serverless
    finally:
        if process_id in monitoring_threads:
            del monitoring_threads[process_id]


def stream_process_output(proc, process_id):
    """Stream stdout/stderr to clients and clean up afterward"""
    output_lines = []
    try:
        for line in proc.stdout:
            try:
                socketio.emit('output', {
                    'process_id': process_id,
                    'line': line.rstrip('\n')
                })
            except Exception:
                pass  # SocketIO may not work in serverless
            output_lines.append(line)
    except Exception as e:
        try:
            socketio.emit('error', {'message': f'Output stream error: {str(e)}'})
        except Exception:
            pass  # SocketIO may not work in serverless
    finally:
        if proc.stdout:
            try:
                proc.stdout.close()
            except Exception:
                pass

    return_code = proc.wait()
    output = ''.join(output_lines)

    try:
        socketio.emit('process_complete', {
            'process_id': process_id,
            'return_code': return_code,
            'output': output
        })
    except Exception:
        pass  # SocketIO may not work in serverless

    cleanup_process_resources(process_id)

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_code():
    """Analyze code for vulnerabilities"""
    if 'file' not in request.files:
        data = request.json
        if data and 'file_path' in data:
            file_path = data.get('file_path')
            if file_path and os.path.exists(file_path):
                analyzer = CodeAnalyzer()
                result = analyzer.analyze_file(file_path)
                return jsonify(result)
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save uploaded file temporarily
    ensure_upload_dir()
    original_name = secure_filename(file.filename) or f"upload_{uuid.uuid4().hex}"
    file_path = UPLOAD_DIR / original_name
    file.save(str(file_path))
    
    try:
        analyzer = CodeAnalyzer()
        result = analyzer.analyze_file(str(file_path))
        return jsonify(result)
    finally:
        # Clean up uploaded file
        file_path_obj = Path(file_path)
        if file_path_obj.exists():
            file_path_obj.unlink(missing_ok=True)

@app.route('/api/run', methods=['POST'])
def run_sandbox():
    """Run a command in the sandbox"""
    data = request.json
    command = data.get('command')
    args = data.get('args', [])
    limits = data.get('limits', {})
    
    try:
        if not command or not str(command).strip():
            return jsonify({'error': 'Command is required. Please enter a command to execute.'}), 400
        
        if isinstance(command, str):
            command_parts = shlex.split(command)
        else:
            command_parts = [command]

        if args:
            command_parts.extend(args)

        process_id, pid = launch_sandbox_process(
            command_parts,
            limits,
            metadata={}
        )

        return jsonify({
            'success': True,
            'process_id': process_id,
            'pid': pid
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze-run', methods=['POST'])
def analyze_and_run():
    """Analyze selected file and run it inside the sandbox"""
    file_storage = request.files.get('file')
    manual_path = request.form.get('file_path', '').strip()

    saved_path = None
    uploaded = False

    if file_storage and file_storage.filename:
        try:
            saved_path = save_uploaded_file(file_storage)
            uploaded = True
        except Exception as e:
            return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
    elif manual_path:
        candidate = Path(manual_path).expanduser()
        try:
            candidate = candidate.resolve()
        except FileNotFoundError:
            candidate = None
        if not candidate or not candidate.exists():
            return jsonify({'error': f'File not found: {manual_path}'}), 400
        saved_path = candidate
    else:
        return jsonify({'error': 'No file provided'}), 400

    saved_path = Path(saved_path).resolve()

    analyzer = CodeAnalyzer()
    analysis_result = analyzer.analyze_file(str(saved_path))

    limits = {
        'cpu': request.form.get('cpu') or None,
        'memory': request.form.get('memory') or None,
        'processes': request.form.get('processes') or None,
        'file_size': request.form.get('file_size') or None
    }

    try:
        command_parts, cleanup_paths = build_execution_command(saved_path)
        metadata = {
            'uploaded_file': str(saved_path) if uploaded else None,
            'cleanup_paths': cleanup_paths
        }
        process_id, pid = launch_sandbox_process(command_parts, limits, metadata)

        return jsonify({
            'success': True,
            'process_id': process_id,
            'pid': pid,
            'analysis': analysis_result,
            'command': command_parts
        })
    except Exception as e:
        if uploaded and saved_path.exists():
            try:
                saved_path.unlink(missing_ok=True)
            except Exception:
                pass
        return jsonify({
            'error': str(e),
            'analysis': analysis_result
        }), 400

@app.route('/api/stop/<process_id>', methods=['POST'])
def stop_process(process_id):
    """Stop a running process"""
    if process_id in running_processes:
        proc = running_processes[process_id]['process']
        proc.terminate()
        return jsonify({'success': True})
    return jsonify({'error': 'Process not found'}), 404

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get status of all processes"""
    status = []
    for pid, info in running_processes.items():
        try:
            proc = info['process']
            if proc.poll() is None:  # Still running
                status.append({
                    'process_id': pid,
                    'pid': info['pid'],
                    'command': info['command'],
                    'running': True
                })
        except:
            pass
    return jsonify(status)

@socketio.on('send_input')
def handle_send_input(data):
    """Handle interactive input from the browser terminal"""
    process_id = data.get('process_id')
    text = data.get('text', '')

    if not process_id or process_id not in running_processes or text is None:
        return

    proc_info = running_processes.get(process_id)
    proc = proc_info.get('process') if proc_info else None
    stdin = proc_info.get('stdin') if proc_info else None

    if proc is None or proc.poll() is not None or stdin is None:
        return

    append_newline = data.get('append_newline', True)

    try:
        if append_newline and not text.endswith('\n'):
            stdin.write(text + '\n')
        else:
            stdin.write(text)
        stdin.flush()
    except Exception as e:
        try:
            socketio.emit('error', {'message': f'Failed to send input: {str(e)}'})
        except Exception:
            pass  # SocketIO may not work in serverless

# Export app for Vercel serverless function
# Vercel's @vercel/python will automatically detect the Flask app
# Both 'app' and 'handler' are available for compatibility
handler = app

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    ensure_upload_dir()
    
    # Check if running on Vercel
    if os.environ.get('VERCEL'):
        print("🌐 Running on Vercel")
        # Vercel handles the server - app is already exported as 'handler'
    else:
        print("🚀 Starting ZenCube Web Dashboard...")
        print("📊 Server will be available at:")
        print("   http://localhost:5000")
        print("   http://127.0.0.1:5000")
        print("\n⏹️  Press Ctrl+C to stop\n")
        try:
            socketio.run(app, host='127.0.0.1', port=5000, debug=False, allow_unsafe_werkzeug=True)
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"\n❌ Port 5000 is already in use")
                print("Try: lsof -ti:5000 | xargs kill")
                print("Or use a different port")
            else:
                print(f"\n❌ Error: {e}")
                raise

