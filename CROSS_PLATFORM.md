# Cross-Platform Support

ZenCube is **fully universal** and automatically detects the platform it's running on. There is **no need to comment/uncomment code** for different platforms - it works seamlessly on Windows, macOS, and Linux.

## How It Works

### C Code (`sandbox.c`)
The C code uses **preprocessor directives** to automatically detect the platform at compile time:
- `#ifdef _WIN32` - Windows-specific code
- `#else` - Unix-like systems (macOS, Linux, BSD)
- The compiler automatically selects the correct code path based on the target platform

### Python Code
All Python files use **runtime platform detection**:
- `platform_utils.py` - Centralized platform utility module
- All files use this module for consistent platform detection
- Automatically detects Windows, macOS, and Linux at runtime

## Platform Detection

The codebase uses the following detection methods:

1. **`platform_utils.py`** - Central utility module with:
   - `IS_WINDOWS` - True if running on Windows
   - `IS_MACOS` - True if running on macOS  
   - `IS_LINUX` - True if running on Linux
   - `IS_UNIX` - True if running on Unix-like systems (macOS, Linux, BSD)
   - Platform-specific utility functions

2. **C Preprocessor** - In `sandbox.c`:
   - `#ifdef _WIN32` - Windows detection
   - Automatically handled by the compiler

## Key Features

✅ **Automatic Platform Detection** - No manual configuration needed
✅ **Consistent API** - Same functions work on all platforms
✅ **Platform-Specific Optimizations** - Automatically applies platform-specific code
✅ **No Code Commenting** - All code is active, selected automatically

## Building on Different Platforms

### Windows
```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
# Or use: python build.py
```

### macOS/Linux
```bash
make
# Or use: python build.py
# Or use: cmake -B build && cmake --build build
```

The build system automatically detects the platform and uses the appropriate compiler and flags.

## Running on Different Platforms

Simply run:
```bash
python run.py
```

Or start the web dashboard:
```bash
python web_dashboard.py
```

The code automatically:
- Detects the platform
- Finds the correct sandbox executable (`sandbox` or `sandbox.exe`)
- Uses platform-appropriate paths and commands
- Handles platform-specific features (like macOS quarantine removal)

## Platform-Specific Behaviors

The code automatically adapts to platform differences:

- **Windows**: Uses `.exe` extensions, Windows API for process management
- **macOS**: Handles quarantine attributes, uses POSIX APIs
- **Linux**: Uses POSIX APIs, full resource limit support

All of this happens automatically - you don't need to change any code!

## Example: Finding the Sandbox Executable

**Before (manual platform detection in each file):**
```python
if platform.system() == "Windows":
    sandbox_path = "./sandbox.exe"
else:
    sandbox_path = "./sandbox"
```

**After (universal):**
```python
from platform_utils import find_sandbox
sandbox_path = find_sandbox()  # Works on all platforms!
```

## Summary

**ZenCube is already universal!** There is no Windows-specific code that needs to be commented out. The code automatically:

1. Detects the platform at compile time (C code) or runtime (Python code)
2. Selects the appropriate code path
3. Uses platform-specific APIs and features
4. Handles platform differences transparently

You can use the same codebase on Windows, macOS, and Linux without any modifications!

