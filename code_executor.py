"""
Code Executor - Safe Python code execution with timeout and output capture
"""
import subprocess
import sys
import os
import tempfile
import time
import re


class CodeExecutor:
    def __init__(self, timeout=30, python_path=None):
        self.timeout = timeout
        self.python_path = python_path or sys.executable
        self.last_code = None
        self.last_output = None
        self.last_error = None
        self.last_returncode = None
        self.work_dir = tempfile.mkdtemp(prefix="agent_exec_")
        self.input_callback = None  # GUI callback for input()

    def set_input_callback(self, callback):
        """Set a callback function for handling input() prompts.
        callback(prompt_text) -> user_value or None to cancel
        """
        self.input_callback = callback

    def _detect_inputs(self, code):
        """Detect input() calls and return list of (full_match, prompt_text)."""
        pattern = r'input\s*\(\s*(?:f?["\x27](.*?)["\x27])?\s*\)'
        matches = []
        for m in re.finditer(pattern, code):
            full = m.group(0)
            prompt = m.group(1) if m.group(1) else "Enter value"
            matches.append((full, prompt))
        return matches

    def _replace_inputs(self, code, values):
        """Replace input() calls with provided values."""
        result = code
        for (full_match, _), value in zip(self._detect_inputs(code), values):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            result = result.replace(full_match, f'"{escaped}"', 1)
        return result

    def execute(self, code, input_data=None):
        """
        Execute Python code in a subprocess.
        If input() calls are detected and a callback is set,
        prompts the user via GUI and replaces them.
        Returns (success, stdout, stderr, execution_time)
        """
        self.last_code = code

        # Detect and handle input() calls
        inputs = self._detect_inputs(code)
        if inputs and self.input_callback and input_data is None:
            values = []
            for full_match, prompt in inputs:
                value = self.input_callback(prompt)
                if value is None:  # User cancelled
                    return False, "", "Cancelled by user", 0.0
                values.append(value)
            code = self._replace_inputs(code, values)

        # Write code to temp file
        code_file = os.path.join(self.work_dir, "run_code.py")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        start_time = time.time()

        try:
            result = subprocess.run(
                [self.python_path, code_file],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=self.timeout,
                cwd=self.work_dir,
                input=input_data,
                env=self._safe_env()
            )

            elapsed = time.time() - start_time
            self.last_output = result.stdout
            self.last_error = result.stderr
            self.last_returncode = result.returncode

            success = result.returncode == 0
            return success, result.stdout, result.stderr, elapsed

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            self.last_error = f"Execution timed out ({self.timeout}s)"
            self.last_returncode = -1
            return False, "", self.last_error, elapsed

        except Exception as e:
            elapsed = time.time() - start_time
            self.last_error = str(e)
            self.last_returncode = -1
            return False, "", str(e), elapsed

    def execute_with_file(self, code, file_path):
        """Execute code that operates on a specific file."""
        if file_path and os.path.isfile(file_path):
            import shutil
            dest = os.path.join(self.work_dir, os.path.basename(file_path))
            shutil.copy2(file_path, dest)
        return self.execute(code)

    def _safe_env(self):
        """Create a restricted environment for code execution."""
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        return env

    def get_work_dir(self):
        return self.work_dir

    def cleanup(self):
        import shutil
        try:
            if os.path.exists(self.work_dir):
                shutil.rmtree(self.work_dir, ignore_errors=True)
        except Exception:
            pass

    def save_code(self, code, filepath):
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            return True, f"Saved to {filepath}"
        except Exception as e:
            return False, str(e)
