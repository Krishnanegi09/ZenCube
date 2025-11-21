#!/usr/bin/env python3
"""
Platform Utilities for ZenCube
Universal platform detection and utilities that work on Windows, macOS, and Linux
"""

import os
import platform
import sys

# Platform detection
IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"
IS_UNIX = os.name != "nt"  # Unix-like systems (macOS, Linux, BSD, etc.)

def get_platform_name():
    """Get human-readable platform name"""
    system = platform.system()
    if system == "Windows":
        return "Windows"
    elif system == "Darwin":
        return "macOS"
    elif system == "Linux":
        return "Linux"
    else:
        return system

def get_sandbox_executable_name():
    """Get the sandbox executable name for the current platform"""
    return "sandbox.exe" if IS_WINDOWS else "sandbox"

def find_sandbox():
    """Find sandbox executable - works on all platforms"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Common paths to check
    paths = [
        os.path.join(script_dir, "sandbox"),
        os.path.join(script_dir, "sandbox.exe"),
        os.path.join(script_dir, "build", "sandbox"),
        os.path.join(script_dir, "build", "Release", "sandbox.exe"),
        os.path.join(script_dir, "build", "Debug", "sandbox.exe"),
        "./sandbox",
        "./sandbox.exe"
    ]
    
    for path in paths:
        full_path = os.path.abspath(path)
        if os.path.exists(full_path):
            # On Unix-like systems, check if executable
            if IS_UNIX:
                if os.access(full_path, os.X_OK):
                    return full_path
            else:
                # On Windows, just check if file exists
                return full_path
    
    return None

def remove_quarantine_if_needed(file_path):
    """Remove macOS quarantine attribute if present (macOS only, no-op on other platforms)"""
    if not IS_MACOS:
        return
    
    try:
        # Check if quarantine attribute exists
        result = __import__('subprocess').run(
            ["xattr", "-l", file_path],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "com.apple.quarantine" in result.stdout:
            # Remove quarantine attribute
            __import__('subprocess').run(
                ["xattr", "-d", "com.apple.quarantine", file_path],
                capture_output=True,
                timeout=5
            )
    except (__import__('subprocess').TimeoutExpired, FileNotFoundError, __import__('subprocess').CalledProcessError):
        # Silently fail if xattr doesn't exist or can't remove
        pass

def get_python_interpreter():
    """Get the appropriate Python interpreter name for the platform"""
    return "python" if IS_WINDOWS else "python3"

def get_executable_extension():
    """Get executable extension for the current platform"""
    return ".exe" if IS_WINDOWS else ""

def make_executable(file_path):
    """Make a file executable (Unix-like only, no-op on Windows)"""
    if IS_UNIX:
        os.chmod(file_path, 0o755)

def get_test_executable_name(name):
    """Get test executable name with proper extension"""
    return name + ".exe" if IS_WINDOWS else name

def is_executable_file(file_path):
    """Check if a file is executable"""
    if IS_WINDOWS:
        # On Windows, check if file has .exe extension or is in PATH
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".exe" or ext == ".bat" or ext == ".cmd":
            return True
        # Check if it's a command in PATH
        import shutil
        return shutil.which(file_path) is not None
    else:
        # On Unix-like, check execute permission
        return os.path.exists(file_path) and os.access(file_path, os.X_OK)

# Export commonly used functions
__all__ = [
    'IS_WINDOWS',
    'IS_MACOS', 
    'IS_LINUX',
    'IS_UNIX',
    'get_platform_name',
    'get_sandbox_executable_name',
    'find_sandbox',
    'remove_quarantine_if_needed',
    'get_python_interpreter',
    'get_executable_extension',
    'make_executable',
    'get_test_executable_name',
    'is_executable_file'
]

