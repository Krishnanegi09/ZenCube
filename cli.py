#!/usr/bin/env python3
"""
ZenCube Enhanced CLI
Command-line interface with code analysis and monitoring
"""

import argparse
import sys
import os
import json
import subprocess
from code_analyzer import CodeAnalyzer
from platform_utils import find_sandbox

def analyze_command(args):
    """Analyze code for vulnerabilities"""
    analyzer = CodeAnalyzer()
    result = analyzer.analyze_file(args.file)
    
    print(f"\n{'='*60}")
    print(f"Code Analysis Report: {args.file}")
    print(f"{'='*60}\n")
    
    print(f"Total Issues: {result['total_issues']}")
    print(f"  Critical: {result['critical']}")
    print(f"  High: {result['high']}")
    print(f"  Medium: {result['medium']}\n")
    
    if result['vulnerabilities']:
        print("VULNERABILITIES:")
        print("-" * 60)
        for vuln in result['vulnerabilities']:
            print(f"\n[{vuln['severity']}] {vuln['type']}")
            print(f"  Line {vuln['line']}: {vuln['message']}")
            print(f"  Code: {vuln['code']}")
    
    if result['warnings']:
        print("\nWARNINGS:")
        print("-" * 60)
        for warn in result['warnings']:
            print(f"\n[{warn['severity']}] {warn['type']}")
            print(f"  Line {warn['line']}: {warn['message']}")
            print(f"  Code: {warn['code']}")
    
    if args.json:
        print("\n" + json.dumps(result, indent=2))
    
    return 0 if result['total_issues'] == 0 else 1

def run_command(args):
    """Run command in sandbox"""
    sandbox_path = find_sandbox()
    if not sandbox_path:
        print("Error: Sandbox executable not found", file=sys.stderr)
        return 1
    
    cmd = [sandbox_path]
    
    if args.cpu:
        cmd.append(f"--cpu={args.cpu}")
    if args.memory:
        cmd.append(f"--mem={args.memory}")
    if args.processes:
        cmd.append(f"--procs={args.processes}")
    if args.file_size:
        cmd.append(f"--fsize={args.file_size}")
    
    cmd.extend(args.command)
    
    try:
        result = subprocess.run(cmd, text=True)
        return result.returncode
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def monitor_command(args):
    """Monitor a running process"""
    import psutil
    import time
    
    try:
        pid = int(args.pid)
        proc = psutil.Process(pid)
        
        print(f"Monitoring process {pid}...")
        print(f"{'Time':<10} {'CPU%':<10} {'Memory(MB)':<15} {'Threads':<10}")
        print("-" * 50)
        
        start_time = time.time()
        while proc.is_running():
            cpu = proc.cpu_percent(interval=1)
            mem = proc.memory_info().rss / 1024 / 1024
            threads = proc.num_threads()
            elapsed = time.time() - start_time
            
            print(f"{elapsed:<10.1f} {cpu:<10.1f} {mem:<15.2f} {threads:<10}")
            time.sleep(1)
        
        print("\nProcess completed.")
        return 0
    except psutil.NoSuchProcess:
        print(f"Error: Process {args.pid} not found", file=sys.stderr)
        return 1
    except ValueError:
        print(f"Error: Invalid PID: {args.pid}", file=sys.stderr)
        return 1

def main():
    parser = argparse.ArgumentParser(
        description='ZenCube Enhanced CLI - Sandbox with Code Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze script.py
  %(prog)s run --cpu=5 python3 script.py
  %(prog)s monitor 12345
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze code for vulnerabilities')
    analyze_parser.add_argument('file', help='File to analyze')
    analyze_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run command in sandbox')
    run_parser.add_argument('--cpu', type=int, help='CPU time limit (seconds)')
    run_parser.add_argument('--memory', type=int, help='Memory limit (MB)')
    run_parser.add_argument('--processes', type=int, help='Process limit')
    run_parser.add_argument('--file-size', type=int, help='File size limit (MB)')
    run_parser.add_argument('command', nargs=argparse.REMAINDER, help='Command to run')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor a running process')
    monitor_parser.add_argument('pid', help='Process ID to monitor')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'analyze':
        return analyze_command(args)
    elif args.command == 'run':
        return run_command(args)
    elif args.command == 'monitor':
        return monitor_command(args)
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())





