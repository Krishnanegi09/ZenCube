#!/usr/bin/env python3
"""
ZenCube Sandbox Test GUI
A simple GUI for uploading files and testing them with the ZenCube sandbox
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import platform
import shlex
from code_analyzer import CodeAnalyzer
from platform_utils import (
    IS_WINDOWS, IS_UNIX,
    find_sandbox as platform_find_sandbox,
    is_executable_file
)

class SandboxTestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ZenCube Sandbox Studio")
        self.root.geometry("1100x760")
        self.root.minsize(900, 640)
        
        # Styling
        self.style = ttk.Style()
        self.apply_styles()
        
        # Variables
        self.selected_file = None
        self.sandbox_path = self.find_sandbox()
        self.is_running = False
        self.compiled_files = []  # Track compiled files for cleanup
        self.current_process = None
        self.process_stdin = None
        self.input_start_marker = None
        self.waiting_for_input = False
        self.current_input_line = ""
        self.last_command = []
        self.analyzer = CodeAnalyzer()
        
        # Resource limit variables
        self.cpu_enabled = tk.BooleanVar(value=False)
        self.cpu_value = tk.StringVar(value="5")
        self.mem_enabled = tk.BooleanVar(value=False)
        self.mem_value = tk.StringVar(value="100")
        self.procs_enabled = tk.BooleanVar(value=False)
        self.procs_value = tk.StringVar(value="10")
        self.fsize_enabled = tk.BooleanVar(value=False)
        self.fsize_value = tk.StringVar(value="50")
        
        # Create UI
        self.create_widgets()
        self.show_ready_message()
        
        # Check sandbox
        if not self.sandbox_path:
            messagebox.showwarning(
                "Sandbox Not Found",
                "Sandbox executable not found!\n\n"
                "Please build the project first:\n"
                "  make\n\n"
                "Or place sandbox.exe in the project directory."
            )
    
    def apply_styles(self):
        """Apply custom styling for the modern UI"""
        palette = {
            "background": "#0f172a",
            "card": "#111c2f",
            "terminal": "#0b1120",
            "terminal_header": "#1e293b",
            "text_primary": "#e2e8f0",
            "text_secondary": "#94a3b8",
            "accent": "#38bdf8",
            "accent_hover": "#0ea5e9",
            "danger": "#f87171",
            "danger_hover": "#ef4444",
            "terminal_prompt": "#22d3ee",
            "terminal_input": "#facc15",
        }
        
        # Use clam theme for better ttk styling support
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        
        self.root.configure(bg=palette["background"])
        
        # Frame styles
        self.style.configure("App.TFrame", background=palette["background"])
        self.style.configure("Card.TLabelframe", background=palette["card"], foreground=palette["text_primary"], borderwidth=0)
        self.style.configure("Card.TLabelframe.Label", background=palette["card"], foreground=palette["accent"], font=("Segoe UI", 12, "bold"))
        self.style.configure("TerminalOuter.TFrame", background=palette["card"], borderwidth=0)
        self.style.configure("TerminalHeader.TFrame", background=palette["terminal_header"])
        
        # Label styles
        self.style.configure("Title.TLabel", background=palette["background"], foreground=palette["accent"], font=("Segoe UI", 20, "bold"))
        self.style.configure("Subtitle.TLabel", background=palette["background"], foreground=palette["text_secondary"], font=("Segoe UI", 11))
        self.style.configure("App.TLabel", background=palette["background"], foreground=palette["text_primary"])
        self.style.configure("TerminalHeader.TLabel", background=palette["terminal_header"], foreground=palette["text_primary"], font=("Consolas", 11, "bold"))
        self.style.configure("Status.TLabel", background=palette["card"], foreground=palette["text_secondary"], padding=6)
        self.style.configure("Result.TLabel", background=palette["background"], foreground=palette["text_primary"], font=("Segoe UI", 12, "bold"))
        self.style.configure("App.TCheckbutton", background=palette["card"], foreground=palette["text_primary"])
        
        # Button styles
        self.style.configure("Accent.TButton", font=("Segoe UI", 12, "bold"), padding=10)
        self.style.map(
            "Accent.TButton",
            background=[("disabled", "#1e293b"), ("pressed", palette["accent_hover"]), ("active", palette["accent_hover"]), ("!disabled", palette["accent"])],
            foreground=[("disabled", "#64748b"), ("!disabled", "#0f172a")]
        )
        
        self.style.configure("Secondary.TButton", font=("Segoe UI", 11), padding=8, background=palette["terminal_header"], foreground=palette["text_primary"])
        self.style.map(
            "Secondary.TButton",
            background=[("disabled", "#1e293b"), ("active", palette["accent_hover"]), ("pressed", palette["accent_hover"]), ("!disabled", palette["terminal_header"])],
            foreground=[("disabled", "#475569"), ("!disabled", palette["text_primary"])]
        )
        
        self.style.configure("Danger.TButton", font=("Segoe UI", 11, "bold"), padding=8)
        self.style.map(
            "Danger.TButton",
            background=[("disabled", "#1e293b"), ("active", palette["danger_hover"]), ("pressed", palette["danger_hover"]), ("!disabled", palette["danger"])],
            foreground=[("disabled", "#475569"), ("!disabled", "#0f172a")]
        )

    def find_sandbox(self):
        """Find the sandbox executable - uses universal platform detection"""
        return platform_find_sandbox()
    
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Main container
        main_frame = ttk.Frame(self.root, padding=20, style="App.TFrame")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        for col in range(3):
            main_frame.columnconfigure(col, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Header
        title_label = ttk.Label(main_frame, text="ZenCube Sandbox Studio", style="Title.TLabel")
        title_label.grid(row=0, column=0, columnspan=3, sticky=tk.W)
        
        subtitle_label = ttk.Label(
            main_frame,
            text="Analyze, secure, and execute untrusted code in a safe, interactive sandbox.",
            style="Subtitle.TLabel"
        )
        subtitle_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(2, 15))
        
        # File Selection Section
        file_frame = ttk.LabelFrame(main_frame, text="1. Select File", padding=15, style="Card.TLabelframe")
        file_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 12))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(
            file_frame,
            text="📁 Browse File",
            command=self.browse_file,
            style="Secondary.TButton"
        ).grid(row=0, column=0, padx=(0, 12))
        
        self.file_label = ttk.Label(
            file_frame,
            text="No file selected • Supported: executables, .py, .java, .c, .cpp, .sh, .js, .rb, .pl",
            style="App.TLabel"
        )
        self.file_label.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Auto-compile toggle for compiled languages
        self.auto_compile = tk.BooleanVar(value=True)
        self.compile_checkbox = ttk.Checkbutton(
            file_frame,
            text="Auto-compile C/C++/Java before running",
            variable=self.auto_compile,
            style="App.TCheckbutton"
        )
        self.compile_checkbox.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        # Resource Limits Section
        limits_frame = ttk.LabelFrame(main_frame, text="2. Optional Resource Limits", padding=15, style="Card.TLabelframe")
        limits_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 12))
        
        # CPU limit
        cpu_frame = ttk.Frame(limits_frame, style="App.TFrame")
        cpu_frame.grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Checkbutton(cpu_frame, text="CPU Time (seconds)", variable=self.cpu_enabled, style="App.TCheckbutton").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(cpu_frame, textvariable=self.cpu_value, width=10).grid(row=0, column=1)
        
        # Memory limit
        mem_frame = ttk.Frame(limits_frame, style="App.TFrame")
        mem_frame.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(24, 0))
        ttk.Checkbutton(mem_frame, text="Memory (MB)", variable=self.mem_enabled, style="App.TCheckbutton").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(mem_frame, textvariable=self.mem_value, width=10).grid(row=0, column=1)
        
        # Process limit
        procs_frame = ttk.Frame(limits_frame, style="App.TFrame")
        procs_frame.grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Checkbutton(procs_frame, text="Max Processes", variable=self.procs_enabled, style="App.TCheckbutton").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(procs_frame, textvariable=self.procs_value, width=10).grid(row=0, column=1)
        
        # File size limit
        fsize_frame = ttk.Frame(limits_frame, style="App.TFrame")
        fsize_frame.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(24, 0))
        ttk.Checkbutton(fsize_frame, text="File Size (MB)", variable=self.fsize_enabled, style="App.TCheckbutton").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(fsize_frame, textvariable=self.fsize_value, width=10).grid(row=0, column=1)
        
        # Action button row
        button_frame = ttk.Frame(main_frame, style="App.TFrame")
        button_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 12))
        button_frame.columnconfigure(0, weight=1)
        
        self.analyze_run_button = ttk.Button(
            button_frame,
            text="🔍 Analyze & Run in Sandbox",
            command=self.analyze_and_run,
            style="Accent.TButton"
        )
        self.analyze_run_button.grid(row=0, column=0, padx=4, pady=4, ipadx=12)
        self.analyze_run_button.config(state=tk.DISABLED)
        
        # Terminal container
        terminal_container = ttk.Frame(main_frame, style="TerminalOuter.TFrame", padding=0)
        terminal_container.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        terminal_container.columnconfigure(0, weight=1)
        terminal_container.rowconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        terminal_header = ttk.Frame(terminal_container, style="TerminalHeader.TFrame", padding=(16, 10))
        terminal_header.grid(row=0, column=0, sticky=(tk.W, tk.E))
        terminal_header.columnconfigure(0, weight=1)
        
        terminal_title = ttk.Label(terminal_header, text="Interactive Sandbox Terminal", style="TerminalHeader.TLabel")
        terminal_title.grid(row=0, column=0, sticky=tk.W)
        
        self.stop_button = ttk.Button(
            terminal_header,
            text="⏹ Stop",
            command=self.stop_test,
            state=tk.DISABLED,
            style="Danger.TButton"
        )
        self.stop_button.grid(row=0, column=1, padx=(12, 0))
        
        self.clear_button = ttk.Button(
            terminal_header,
            text="🧹 Clear",
            command=lambda: self.clear_output(show_ready=True),
            style="Secondary.TButton"
        )
        self.clear_button.grid(row=0, column=2, padx=(12, 0))
        
        # Terminal text widget
        self.output_text = scrolledtext.ScrolledText(
            terminal_container,
            wrap=tk.WORD,
            font=("Consolas", 11),
            bg="#0b1120",
            fg="#d4d4d4",
            insertbackground="#ffffff",
            selectbackground="#334155",
            selectforeground="#f8fafc",
            borderwidth=0,
            highlightthickness=0,
            undo=False
        )
        self.output_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.output_text.tag_configure("prompt", foreground="#22d3ee", font=("Consolas", 11, "bold"))
        self.output_text.tag_configure("input", foreground="#facc15")
        self.output_text.tag_configure("analysis", foreground="#a855f7", font=("Consolas", 11, "bold"))
        
        # Terminal prompt marker
        self.input_start_marker = None
        self.waiting_for_input = False
        
        # Bind keyboard events for terminal-like input
        self.output_text.bind('<KeyPress>', self.on_key_press)
        self.output_text.bind('<Return>', self.on_enter_key)
        self.output_text.bind('<BackSpace>', self.on_backspace)
        self.output_text.bind('<Button-1>', self.on_click)
        self.output_text.bind('<Key>', self.on_any_key)
        self.output_text.focus_set()
        
        # Status Bar & result
        self.status_label = ttk.Label(
            main_frame,
            text="Status: Ready",
            style="Status.TLabel",
            anchor=tk.W
        )
        self.status_label.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(12, 0))
        
        self.result_label = ttk.Label(
            main_frame,
            text="",
            style="Result.TLabel"
        )
        self.result_label.grid(row=7, column=0, columnspan=3, pady=(6, 0), sticky=tk.W)
        
        # Focus terminal after window loads
        self.root.after(150, self.output_text.focus_set)
    
    def show_ready_message(self):
        """Display instructions or hints when idle"""
        if self.is_running:
            return
        
        content = self.output_text.get("1.0", tk.END).strip()
        if content:
            self.log_output('\n💡 Sandbox idle. Select a file and click "Analyze & Run in Sandbox" to start again.\n', tag="analysis")
            self.update_status("Ready - select a new file or rerun the current one")
            return
        
        intro = (
            "🧊 ZenCube Sandbox Studio\n"
            "-------------------------\n"
            "1. Click \"📁 Browse File\" to choose the code you want to test.\n"
            "2. (Optional) Adjust CPU, memory, process, or file limits.\n"
            "3. Press \"Analyze & Run in Sandbox\" to scan and execute.\n"
            "Tip: Works with Python, Java, C/C++, Shell, JavaScript, Ruby, and more.\n\n"
        )
        self.log_output(intro, tag="analysis")
        self.update_status("Ready - select a file, then click Analyze & Run")
    
    def browse_file(self):
        """Open file dialog to select a file"""
        file_path = filedialog.askopenfilename(
            title="Select File to Test",
            filetypes=[
                ("All Supported", "*.exe *.bin *.py *.java *.c *.cpp *.cc *.cxx *.sh *.js *.rb *.pl"),
                ("Executables", "*.exe *.bin"),
                ("Python Files", "*.py"),
                ("Java Files", "*.java"),
                ("C Files", "*.c"),
                ("C++ Files", "*.cpp *.cc *.cxx"),
                ("Shell Scripts", "*.sh"),
                ("JavaScript", "*.js"),
                ("All Files", "*.*")
            ]
        )
        
        if file_path:
            self.selected_file = file_path
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Detect file type
            file_type = "Executable"
            needs_compile = False
            if file_ext == '.py':
                file_type = "Python script"
            elif file_ext == '.java':
                file_type = "Java source"
                needs_compile = True
            elif file_ext == '.c':
                file_type = "C source"
                needs_compile = True
            elif file_ext in ['.cpp', '.cc', '.cxx']:
                file_type = "C++ source"
                needs_compile = True
            elif file_ext == '.sh':
                file_type = "Shell script"
            elif file_ext == '.js':
                file_type = "JavaScript"
            elif file_ext == '.rb':
                file_type = "Ruby script"
            elif file_ext == '.pl':
                file_type = "Perl script"
            
            # Enable/disable compile checkbox based on file type
            self.compile_checkbox.config(state=tk.NORMAL if needs_compile else tk.DISABLED)
            if not needs_compile:
                self.auto_compile.set(False)
            
            self.file_label.config(
                text=f"Selected: {file_name} ({file_type})",
                foreground="#e2e8f0"
            )
            self.log_output(f"✅ File selected: {file_path} ({file_type})\n", tag="analysis")
            self.analyze_run_button.config(state=tk.NORMAL)
            self.update_status(f"Ready to analyze: {file_name}")
    
    def compile_file(self, file_path):
        """Compile C, C++, or Java files"""
        file_ext = os.path.splitext(file_path)[1].lower()
        file_dir = os.path.dirname(file_path)
        file_base = os.path.splitext(os.path.basename(file_path))[0]
        
        compiled_path = None
        compile_cmd = None
        
        try:
            if file_ext == '.c':
                # Compile C file
                compiled_path = os.path.join(file_dir, file_base)
                compile_cmd = ['gcc', '-o', compiled_path, file_path]
                self.log_output(f"Compiling C file: gcc -o {compiled_path} {file_path}\n")
                
            elif file_ext in ['.cpp', '.cc', '.cxx']:
                # Compile C++ file
                compiled_path = os.path.join(file_dir, file_base)
                compile_cmd = ['g++', '-o', compiled_path, file_path]
                self.log_output(f"Compiling C++ file: g++ -o {compiled_path} {file_path}\n")
                
            elif file_ext == '.java':
                # Compile Java file
                # Java compiles to .class file in same directory
                compile_cmd = ['javac', file_path]
                class_file = os.path.join(file_dir, f"{file_base}.class")
                self.log_output(f"Compiling Java file: javac {file_path}\n")
                compiled_path = class_file
            
            if compile_cmd:
                # Run compilation
                result = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout
                    raise Exception(f"Compilation failed:\n{error_msg}")
                
                self.log_output("✓ Compilation successful!\n\n")
                
                # For Java, return the class name (without .class extension)
                if file_ext == '.java':
                    return file_base, file_dir
                
                return compiled_path, None
                
        except subprocess.TimeoutExpired:
            raise Exception("Compilation timed out")
        except Exception as e:
            raise Exception(f"Compilation error: {str(e)}")
        
        return None, None
    
    def build_command(self):
        """Build the sandbox command with selected options"""
        if not self.selected_file:
            raise ValueError("No file selected")
        
        if not self.sandbox_path:
            raise ValueError("Sandbox executable not found")
        
        cmd = [self.sandbox_path]
        
        # Add resource limits
        if self.cpu_enabled.get():
            cmd.append(f"--cpu={self.cpu_value.get()}")
        
        if self.mem_enabled.get():
            cmd.append(f"--mem={self.mem_value.get()}")
        
        if self.procs_enabled.get():
            cmd.append(f"--procs={self.procs_value.get()}")
        
        if self.fsize_enabled.get():
            cmd.append(f"--fsize={self.fsize_value.get()}")
        
        # Detect file type and handle compilation if needed
        file_path = self.selected_file
        file_ext = os.path.splitext(file_path)[1].lower()
        file_name = os.path.basename(file_path).lower()
        
        interpreter = None
        exec_file = file_path
        
        # Handle compiled languages (C, C++, Java)
        if file_ext in ['.c', '.cpp', '.cc', '.cxx'] and self.auto_compile.get():
            try:
                compiled_file, _ = self.compile_file(file_path)
                if compiled_file and os.path.exists(compiled_file):
                    exec_file = compiled_file
                else:
                    raise ValueError(f"Compilation failed or output file not found: {compiled_file}")
            except Exception as e:
                raise ValueError(f"Failed to compile {file_path}: {str(e)}")
        
        elif file_ext == '.java' and self.auto_compile.get():
            try:
                class_name, class_dir = self.compile_file(file_path)
                if class_name:
                    interpreter = 'java'
                    # Java needs classpath and class name
                    exec_file = f"-cp {class_dir} {class_name}"
                else:
                    raise ValueError("Java compilation failed - no class file generated")
            except Exception as e:
                raise ValueError(f"Failed to compile Java file {file_path}: {str(e)}")
        
        else:
            # Check for shebang in first line
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('#!'):
                        interpreter = first_line[2:].strip().split()[0]
                        # If it's a path like /usr/bin/env python3, extract python3
                        if '/env' in interpreter:
                            interpreter = first_line.split()[-1]
            except:
                pass
            
            # Determine interpreter based on file extension
            if not interpreter:
                if file_ext == '.py' or file_name.endswith('.py'):
                    interpreter = 'python3'
                elif file_ext == '.sh' or file_name.endswith('.sh'):
                    interpreter = 'bash'
                elif file_ext == '.js' or file_name.endswith('.js'):
                    interpreter = 'node'
                elif file_ext == '.rb' or file_name.endswith('.rb'):
                    interpreter = 'ruby'
                elif file_ext == '.pl' or file_name.endswith('.pl'):
                    interpreter = 'perl'
        
        # Validate exec_file is not empty
        if not exec_file or not exec_file.strip():
            raise ValueError("No executable file or command specified. Please select a valid file.")
        
        # Check if file exists (for non-Java cases)
        if interpreter != 'java' and not os.path.exists(exec_file) and not os.path.isabs(exec_file):
            # Check if it's a command in PATH
            import shutil
            if not shutil.which(exec_file):
                raise ValueError(f"File or command not found: {exec_file}")
        
        # Add interpreter if needed
        if interpreter:
            if interpreter == 'java':
                # Java command is special - it includes classpath in exec_file
                cmd.append(interpreter)
                java_parts = shlex.split(exec_file)
                if not java_parts:
                    raise ValueError("Java execution command is empty. Please check compilation output.")
                cmd.extend(java_parts)
            else:
                cmd.append(interpreter)
                cmd.append(exec_file)
        else:
            # Direct executable - check if it's executable
            if not os.path.exists(exec_file):
                raise ValueError(f"Executable file not found: {exec_file}")
            if not is_executable_file(exec_file):
                raise ValueError(f"File is not executable: {exec_file}")
            cmd.append(exec_file)
        
        # Final validation - ensure command is not empty
        sanitized_cmd = []
        for arg in cmd:
            if arg is None:
                continue
            arg_str = str(arg)
            if arg_str.strip() == "":
                raise ValueError("Command contains an empty argument. Unable to determine executable or interpreter.")
            sanitized_cmd.append(arg_str)
        
        if len(sanitized_cmd) <= 1:  # Only sandbox path, no command
            raise ValueError("Command is empty. Please select a valid file to execute.")
        
        self.last_command = sanitized_cmd
        return sanitized_cmd, interpreter, file_ext
    
    def analyze_and_run(self):
        """Analyze code for vulnerabilities and then run the test"""
        if not self.selected_file:
            messagebox.showwarning("No File Selected", "Please select a file to test first.")
            return
        
        if self.is_running:
            messagebox.showinfo("Test Running", "A test is already running. Please wait or stop it first.")
            return
        
        # Disable buttons, enable stop button
        self.analyze_run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.is_running = True
        self.waiting_for_input = False
        self.result_label.config(text="", foreground="")
        
        # Clear previous output
        self.clear_output(show_ready=False)
        
        # Run analysis and test in thread
        thread = threading.Thread(target=self._analyze_and_run_thread, daemon=True)
        thread.start()
    
    def _analyze_and_run_thread(self):
        """Run analysis first, then execute test"""
        try:
            # Step 1: Code Analysis
            self.log_output("=" * 60 + "\n", tag="analysis")
            self.log_output("🔍 CODE ANALYSIS & VULNERABILITY DETECTION\n", tag="analysis")
            self.log_output("=" * 60 + "\n\n", tag="analysis")
            self.update_status("Analyzing code for vulnerabilities...")
            
            file_ext = os.path.splitext(self.selected_file)[1].lower()
            
            # Check if file type is supported for analysis
            if file_ext in ['.c', '.cpp', '.cc', '.cxx', '.py', '.java']:
                try:
                    analysis_result = self.analyzer.analyze_file(self.selected_file)
                    
                    if "error" in analysis_result:
                        self.log_output(f"⚠️  Analysis Error: {analysis_result['error']}\n\n")
                    else:
                        # Display vulnerabilities
                        if analysis_result.get('vulnerabilities'):
                            self.log_output("🚨 VULNERABILITIES FOUND:\n", tag="analysis")
                            self.log_output("-" * 60 + "\n", tag="analysis")
                            for vuln in analysis_result['vulnerabilities']:
                                self.log_output(f"❌ {vuln['type']}\n")
                                self.log_output(f"   Line {vuln['line']}: {vuln['message']}\n")
                                if 'code' in vuln:
                                    self.log_output(f"   Code: {vuln['code'].strip()}\n")
                                self.log_output("\n")
                        else:
                            self.log_output("✅ No critical vulnerabilities detected!\n\n")
                        
                        # Display warnings
                        if analysis_result.get('warnings'):
                            self.log_output("⚠️  WARNINGS:\n", tag="analysis")
                            self.log_output("-" * 60 + "\n", tag="analysis")
                            for warn in analysis_result['warnings']:
                                self.log_output(f"⚠️  {warn['type']}\n")
                                self.log_output(f"   Line {warn['line']}: {warn['message']}\n\n")
                        
                        # Display info
                        if analysis_result.get('info'):
                            self.log_output("ℹ️  INFORMATION:\n", tag="analysis")
                            self.log_output("-" * 60 + "\n", tag="analysis")
                            for info in analysis_result['info']:
                                self.log_output(f"ℹ️  {info['message']}\n")
                        
                        # Summary
                        vuln_count = len(analysis_result.get('vulnerabilities', []))
                        warn_count = len(analysis_result.get('warnings', []))
                        self.log_output("\n" + "=" * 60 + "\n", tag="analysis")
                        self.log_output(f"📊 Analysis Summary: {vuln_count} vulnerabilities, {warn_count} warnings\n", tag="analysis")
                        self.log_output("=" * 60 + "\n\n", tag="analysis")
                except Exception as e:
                    self.log_output(f"❌ Analysis failed: {str(e)}\n\n")
            else:
                self.log_output(f"ℹ️  Code analysis not available for {file_ext} files\n")
                self.log_output("   (Analysis supports: .c, .cpp, .py, .java)\n\n")
            
            # Step 2: Run the test
            self.log_output("=" * 60 + "\n")
            self.log_output("▶️  RUNNING SANDBOX TEST\n")
            self.log_output("=" * 60 + "\n\n")
            self.update_status("Running sandbox test...")
            
            # Now run the actual test
            self._run_test_thread()
            
        except Exception as e:
            self.log_output(f"\n❌ Error: {str(e)}\n")
            self.result_label.config(text="❌ Error Occurred", foreground="red")
            self.update_status(f"Error: {str(e)}")
        finally:
            # Cleanup
            self.current_process = None
            self.process_stdin = None
            self.is_running = False
            self.waiting_for_input = False
            self.analyze_run_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            # Show idle hint when finished
            if not self.waiting_for_input:
                self.show_ready_message()
    
    def show_prompt(self):
        """Show terminal prompt"""
        if not self.waiting_for_input and self.is_running:
            # Only show prompt if process is running and not already waiting
            self.output_text.insert(tk.END, "$ ", "prompt")
            self.input_start_marker = self.output_text.index(tk.END + "-1c")
            self.output_text.see(tk.END)
            self.waiting_for_input = True
            self.current_input_line = ""
            # Move cursor to after prompt
            self.output_text.mark_set(tk.INSERT, tk.END)
    
    def on_key_press(self, event):
        """Handle key press in terminal"""
        # Only restrict typing when waiting for input - allow normal typing otherwise
        if self.waiting_for_input and self.is_running:
            # When waiting for input, ensure cursor is after prompt
            current_pos = self.output_text.index(tk.INSERT)
            if self.input_start_marker and current_pos < self.input_start_marker:
                # Move cursor to after prompt
                self.output_text.mark_set(tk.INSERT, self.input_start_marker)
        return None
    
    def on_any_key(self, event):
        """Handle any key press"""
        # When waiting for input, ensure we're typing after the prompt
        if self.waiting_for_input and self.is_running:
            current_pos = self.output_text.index(tk.INSERT)
            if self.input_start_marker and current_pos < self.input_start_marker:
                # Prevent editing before prompt - move cursor to after prompt
                self.output_text.mark_set(tk.INSERT, self.input_start_marker)
                return "break"
        return None
    
    def on_enter_key(self, event):
        """Handle Enter key - send input"""
        if not self.waiting_for_input or not self.is_running:
            return None
        
        if not self.process_stdin:
            # Process might not be ready yet
            return None
        
        # Get the current line (after prompt)
        current_pos = self.output_text.index(tk.INSERT)
        if self.input_start_marker:
            try:
                input_text = self.output_text.get(self.input_start_marker, current_pos).strip()
            except:
                input_text = ""
        else:
            input_text = ""
        
        # Send input to process
        try:
            if self.process_stdin and not self.process_stdin.closed:
                self.process_stdin.write(input_text + "\n")
                self.process_stdin.flush()
                # Echo the input (without prompt) and add newline
                if input_text:
                    self.output_text.insert(tk.END, input_text, "input")
                self.output_text.insert(tk.END, "\n")
                # Remove old prompt marker
                self.input_start_marker = None
                self.waiting_for_input = False
                # Wait a bit to see if program outputs something, then show new prompt
                self.root.after(100, self._check_and_show_prompt)
            else:
                self.log_output(f"\n[Error: Process stdin not available]\n")
        except Exception as e:
            self.log_output(f"\n[Error sending input: {str(e)}]\n")
            self.input_start_marker = None
            self.waiting_for_input = False
        
        return "break"
    
    def _check_and_show_prompt(self):
        """Check if we should show prompt after sending input"""
        if self.is_running and not self.waiting_for_input:
            # Check if process is still running and might be waiting
            if self.current_process and self.current_process.poll() is None:
                # Process still running, might be waiting for more input
                self.show_prompt()
    
    def on_backspace(self, event):
        """Handle backspace - prevent deleting prompt"""
        # Only restrict backspace when waiting for input
        if self.waiting_for_input and self.is_running:
            current_pos = self.output_text.index(tk.INSERT)
            if self.input_start_marker and current_pos <= self.input_start_marker:
                # Prevent deleting the prompt
                return "break"
        return None
    
    def on_click(self, event):
        """Handle mouse click - move cursor to end if clicking before prompt"""
        if self.waiting_for_input and self.is_running:
            click_pos = self.output_text.index(f"@{event.x},{event.y}")
            if self.input_start_marker and click_pos < self.input_start_marker:
                # Move cursor to end
                self.output_text.mark_set(tk.INSERT, tk.END)
                return "break"
        return None
    
    def send_input(self):
        """Send input to the running process (legacy method, now handled by on_enter_key)"""
        pass
    
    def _run_test_thread(self):
        """Run the test in background thread"""
        try:
            self.compiled_files = []  # Reset compiled files list
            
            try:
                cmd, interpreter, file_ext = self.build_command()
            except ValueError as e:
                self.log_output(f"\n❌ Error building command: {str(e)}\n")
                self.result_label.config(text="❌ Command Error", foreground="red")
                self.update_status(f"Error: {str(e)}")
                return
            
            # Validate command before running
            if not cmd or len(cmd) <= 1:
                self.log_output(f"\n❌ Error: Empty command generated\n")
                self.result_label.config(text="❌ Empty Command", foreground="red")
                self.update_status("Error: Empty command")
                return
            
            self.log_output("=" * 60 + "\n")
            self.log_output("Starting Sandbox Test\n")
            self.log_output("=" * 60 + "\n\n")
            if interpreter:
                self.log_output(f"File type: {file_ext}, Interpreter: {interpreter}\n")
            display_cmd = " ".join(shlex.quote(part) for part in cmd)
            self.log_output(f"Command: {display_cmd}\n\n")
            self.log_output(f"Full command array: {cmd}\n\n")
            self.update_status("Running test...")
            
            # Run the command
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=0,  # Unbuffered for better real-time output
                universal_newlines=True
            )
            self.process_stdin = self.current_process.stdin
            process = self.current_process
            
            # Read output in real-time
            output_lines = []
            import select
            import time
            
            # For Unix-like systems (macOS, Linux) - use select module
            if IS_UNIX and hasattr(select, 'select'):
                start_time = time.time()
                timeout_seconds = 30  # Timeout for programs waiting for input
                
                while True:
                    if not self.is_running:
                        process.terminate()
                        break
                    
                    # Check if process is still running
                    poll_result = process.poll()
                    if poll_result is not None:
                        # Process ended, read remaining output
                        remaining = process.stdout.read()
                        if remaining:
                            self.log_output(remaining)
                            output_lines.append(remaining)
                        return_code = poll_result
                        break
                    
                    # Check if there's output available (non-blocking)
                    ready, _, _ = select.select([process.stdout], [], [], 0.1)
                    if ready:
                        line = process.stdout.readline()
                        if line:
                            # Remove old prompt if output is coming
                            if self.waiting_for_input and self.input_start_marker:
                                try:
                                    # Remove the prompt line
                                    start_line = self.output_text.index(self.input_start_marker + "-2c")
                                    end_line = self.output_text.index(self.input_start_marker)
                                    self.output_text.delete(start_line, end_line)
                                except:
                                    pass
                                self.input_start_marker = None
                                self.waiting_for_input = False
                            
                            self.log_output(line)
                            output_lines.append(line)
                            start_time = time.time()  # Reset timeout on output
                    else:
                        # Check for timeout - program might be waiting for input
                        # Use a shorter timeout to detect input waiting faster
                        if time.time() - start_time > 0.5 and not self.waiting_for_input and self.is_running:
                            # Show prompt if program appears to be waiting for input
                            # This is a heuristic - if no output for 0.5s, might be waiting
                            self.show_prompt()
                            start_time = time.time()  # Reset timeout
                    
                    self.root.update_idletasks()
                    time.sleep(0.05)  # Small delay to prevent CPU spinning
                
                # Make sure we got the return code
                if return_code is None:
                    return_code = process.wait(timeout=1)
            else:
                # Windows - simpler approach with timeout
                import queue
                import threading as th
                
                def read_output(pipe, q):
                    for line in iter(pipe.readline, ''):
                        q.put(line)
                    pipe.close()
                    q.put(None)
                
                q = queue.Queue()
                th.Thread(target=read_output, args=(process.stdout, q), daemon=True).start()
                
                start_time = time.time()
                timeout_seconds = 30
                
                while True:
                    if not self.is_running:
                        process.terminate()
                        break
                    
                    try:
                        line = q.get(timeout=0.1)
                        if line is None:
                            break
                        
                        # Remove old prompt if output is coming
                        if self.waiting_for_input and self.input_start_marker:
                            try:
                                start_line = self.output_text.index(self.input_start_marker + "-2c")
                                end_line = self.output_text.index(self.input_start_marker)
                                self.output_text.delete(start_line, end_line)
                            except:
                                pass
                            self.input_start_marker = None
                            self.waiting_for_input = False
                        
                        self.log_output(line)
                        output_lines.append(line)
                        start_time = time.time()
                    except queue.Empty:
                        # Use shorter timeout to detect input waiting faster
                        if time.time() - start_time > 0.5 and not self.waiting_for_input and self.is_running:
                            # Show prompt if program appears to be waiting for input
                            self.show_prompt()
                            start_time = time.time()
                        if process.poll() is not None:
                            break
                    
                    self.root.update_idletasks()
                
                return_code = process.wait()
            
            # Analyze results
            output = ''.join(output_lines)
            self.log_output("\n" + "=" * 60 + "\n")
            
            if return_code == 0:
                self.log_output("✓ Test completed successfully!\n")
                self.result_label.config(text="✓ Test Passed", foreground="green")
                self.update_status("Test passed")
            else:
                self.log_output(f"✗ Test failed with exit code: {return_code}\n")
                self.result_label.config(text="✗ Test Failed", foreground="red")
                self.update_status(f"Test failed (exit code: {return_code})")
            
            # Check for resource limit violations
            if "RESOURCE LIMIT VIOLATED" in output or "limit exceeded" in output.lower():
                self.log_output("⚠ Resource limit was exceeded\n")
                self.result_label.config(text="⚠ Resource Limit Exceeded", foreground="orange")
            
            self.log_output("=" * 60 + "\n")
            
        except Exception as e:
            self.log_output(f"\n❌ Error: {str(e)}\n")
            self.result_label.config(text="❌ Error Occurred", foreground="red")
            self.update_status(f"Error: {str(e)}")
        finally:
            # Cleanup
            self.current_process = None
            self.process_stdin = None
            self.is_running = False
            self.waiting_for_input = False
            self.analyze_run_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            # Show idle hint
            if not self.waiting_for_input:
                self.show_ready_message()
    
    def stop_test(self):
        """Stop the running test"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
            except Exception as exc:
                self.log_output(f"\n[Warning: Unable to terminate process cleanly: {exc}]\n")
        
        self.stop_button.config(state=tk.DISABLED)
        self.analyze_run_button.config(state=tk.NORMAL)
        self.waiting_for_input = False
        self.log_output("\n\n⚠ Test stopped by user\n")
        self.result_label.config(text="⚠ Test stopped by user", foreground="#facc15")
        self.update_status("Test stopped")
        self.show_ready_message()
    
    def clear_output(self, show_ready=True):
        """Clear the output text"""
        # Ensure text widget is editable
        if self.output_text.cget('state') == tk.DISABLED:
            self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.result_label.config(text="", foreground="")
        self.input_start_marker = None
        self.waiting_for_input = False
        self.current_input_line = ""
        
        if show_ready and not self.is_running:
            self.show_ready_message()
    
    def log_output(self, text, tag=None):
        """Add text to output window"""
        # Ensure text widget is editable
        if self.output_text.cget('state') == tk.DISABLED:
            self.output_text.config(state=tk.NORMAL)
        
        # If there's a prompt, remove it before adding output
        if self.waiting_for_input and self.input_start_marker:
            try:
                start_line = self.output_text.index(self.input_start_marker + "-2c")
                end_line = self.output_text.index(self.input_start_marker)
                self.output_text.delete(start_line, end_line)
                self.input_start_marker = None
                self.waiting_for_input = False
            except:
                pass
        
        if tag:
            self.output_text.insert(tk.END, text, tag)
        else:
            self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_status(self, message):
        """Update status bar"""
        self.status_label.config(text=f"Status: {message}")
        self.root.update_idletasks()


def main():
    root = tk.Tk()
    app = SandboxTestGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

