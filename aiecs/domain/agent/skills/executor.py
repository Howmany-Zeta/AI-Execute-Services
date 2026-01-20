"""
Skill Script Executor

Provides hybrid script execution with native Python and subprocess modes.
Native mode (default for .py) uses direct import for better performance.
Subprocess mode (default for others) runs scripts in isolated processes.
"""

import asyncio
import importlib.util
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Script execution mode."""
    NATIVE = "native"        # Direct Python import (default for .py)
    SUBPROCESS = "subprocess"  # Subprocess execution (default for non-Python)
    AUTO = "auto"            # Determine based on file extension


@dataclass
class ScriptExecutionResult:
    """Result of script execution."""
    success: bool
    result: Any  # Python object for native, parsed JSON or stdout for subprocess
    error: Optional[str] = None
    execution_time: float = 0.0
    mode_used: ExecutionMode = ExecutionMode.AUTO
    
    # Subprocess-specific fields
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    timed_out: bool = False
    
    @property
    def blocking_error(self) -> bool:
        """Check if this is a blocking error (exit code 2)."""
        return self.exit_code == 2


class SkillScriptExecutor:
    """
    Execute skill scripts with hybrid mode support.
    
    Default: Native mode for Python scripts (direct import)
    Optional: Subprocess mode (developer-declared or non-Python)
    
    Features:
    - Automatic mode selection based on file extension
    - Native execution with async support
    - Subprocess execution with JSON I/O
    - Timeout enforcement
    - Output size limits
    - Security validations
    """
    
    # Interpreter mapping by file extension
    INTERPRETERS = {
        '.py': 'python3',
        '.sh': 'bash',
        '.js': 'node',
        '.rb': 'ruby',
        '.pl': 'perl',
    }
    
    # Entry point function names for native mode (checked in order)
    ENTRY_POINTS = ['execute', 'main', 'run']
    
    def __init__(
        self,
        default_timeout: int = 30,
        max_timeout: int = 600,
        max_output_size: int = 1024 * 1024  # 1MB
    ):
        """
        Initialize script executor.
        
        Args:
            default_timeout: Default timeout in seconds (30s)
            max_timeout: Maximum allowed timeout (600s)
            max_output_size: Maximum output size in bytes (1MB)
        """
        self.default_timeout = default_timeout
        self.max_timeout = max_timeout
        self.max_output_size = max_output_size
    
    async def execute(
        self,
        script_path: Path,
        skill_root: Path,
        input_data: Optional[Dict[str, Any]] = None,
        mode: ExecutionMode = ExecutionMode.AUTO,
        timeout: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> ScriptExecutionResult:
        """
        Execute script with automatic mode selection.
        
        Args:
            script_path: Path to script file
            skill_root: Skill root directory
            input_data: Input data (Python dict for both modes)
            mode: Execution mode (AUTO, NATIVE, SUBPROCESS)
            timeout: Execution timeout in seconds
            env_vars: Additional environment variables (subprocess only)
        
        Returns:
            ScriptExecutionResult with result and metadata
        """
        # Security: Validate path is within skill directory
        try:
            script_path = Path(script_path).resolve()
            skill_root = Path(skill_root).resolve()
            if not str(script_path).startswith(str(skill_root)):
                return ScriptExecutionResult(
                    success=False,
                    result=None,
                    error=f"Script path must be within skill directory: {script_path}",
                    mode_used=mode
                )
        except Exception as e:
            return ScriptExecutionResult(
                success=False,
                result=None,
                error=f"Invalid path: {e}",
                mode_used=mode
            )
        
        if not script_path.exists():
            return ScriptExecutionResult(
                success=False,
                result=None,
                error=f"Script not found: {script_path}",
                mode_used=mode
            )
        
        # Determine actual mode
        actual_mode = self._resolve_mode(script_path, mode)
        
        if actual_mode == ExecutionMode.NATIVE:
            return await self._execute_native(
                script_path, skill_root, input_data, timeout
            )
        else:
            return await self._execute_subprocess(
                script_path, skill_root, input_data, timeout, env_vars
            )

    def _resolve_mode(
        self,
        script_path: Path,
        mode: ExecutionMode
    ) -> ExecutionMode:
        """
        Resolve AUTO mode based on file extension.

        Args:
            script_path: Path to the script
            mode: Requested mode

        Returns:
            Resolved execution mode
        """
        if mode != ExecutionMode.AUTO:
            return mode

        # Python files default to native, others to subprocess
        if script_path.suffix == '.py':
            return ExecutionMode.NATIVE
        return ExecutionMode.SUBPROCESS

    async def _execute_native(
        self,
        script_path: Path,
        skill_root: Path,
        input_data: Optional[Dict[str, Any]],
        timeout: Optional[int]
    ) -> ScriptExecutionResult:
        """
        Execute Python script via direct import.

        Expected script interface:
        ```python
        def execute(input_data: dict) -> dict:
            '''Main entry point'''
            return {"result": "..."}
        ```

        Alternative entry points (checked in order):
        1. execute(input_data) -> result
        2. main(input_data) -> result
        3. run(input_data) -> result
        """
        start_time = time.time()
        effective_timeout = min(timeout or self.default_timeout, self.max_timeout)

        try:
            # Load module from file
            spec = importlib.util.spec_from_file_location(
                f"skill_script_{script_path.stem}",
                script_path
            )

            if spec is None or spec.loader is None:
                return ScriptExecutionResult(
                    success=False,
                    result=None,
                    error=f"Cannot load script: {script_path}",
                    execution_time=time.time() - start_time,
                    mode_used=ExecutionMode.NATIVE
                )

            module = importlib.util.module_from_spec(spec)

            # Add skill_root to module for resource access
            module.__skill_root__ = skill_root

            spec.loader.exec_module(module)

            # Find entry point
            entry_point = None
            for name in self.ENTRY_POINTS:
                if hasattr(module, name) and callable(getattr(module, name)):
                    entry_point = getattr(module, name)
                    break

            if entry_point is None:
                return ScriptExecutionResult(
                    success=False,
                    result=None,
                    error=f"Script missing entry point ({', '.join(self.ENTRY_POINTS)})",
                    execution_time=time.time() - start_time,
                    mode_used=ExecutionMode.NATIVE
                )

            # Execute with timeout
            if asyncio.iscoroutinefunction(entry_point):
                # Async function
                result = await asyncio.wait_for(
                    entry_point(input_data or {}),
                    timeout=effective_timeout
                )
            else:
                # Sync function - run in executor
                loop = asyncio.get_running_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, entry_point, input_data or {}),
                    timeout=effective_timeout
                )

            return ScriptExecutionResult(
                success=True,
                result=result,
                execution_time=time.time() - start_time,
                mode_used=ExecutionMode.NATIVE
            )

        except asyncio.TimeoutError:
            return ScriptExecutionResult(
                success=False,
                result=None,
                error=f"Script execution timed out after {effective_timeout}s",
                execution_time=time.time() - start_time,
                mode_used=ExecutionMode.NATIVE,
                timed_out=True
            )
        except Exception as e:
            return ScriptExecutionResult(
                success=False,
                result=None,
                error=f"Script execution failed: {type(e).__name__}: {str(e)}",
                execution_time=time.time() - start_time,
                mode_used=ExecutionMode.NATIVE
            )

    async def _execute_subprocess(
        self,
        script_path: Path,
        skill_root: Path,
        input_data: Optional[Dict[str, Any]],
        timeout: Optional[int],
        env_vars: Optional[Dict[str, str]]
    ) -> ScriptExecutionResult:
        """
        Execute script via subprocess with flexible I/O.

        Supports multiple I/O patterns:
        1. JSON stdin → JSON stdout (Claude-Code compatible)
        2. Arguments → stdout (simple scripts)
        3. No input → stdout (utility scripts)

        NOT enforcing strict JSON I/O - scripts can use any format.
        """
        start_time = time.time()
        effective_timeout = min(timeout or self.default_timeout, self.max_timeout)

        # Prepare environment
        env = os.environ.copy()
        env['SKILL_ROOT'] = str(skill_root)
        env['AIECS_SCRIPT_MODE'] = 'subprocess'
        if env_vars:
            env.update(env_vars)

        # Get interpreter
        interpreter = self._get_interpreter(script_path)
        if interpreter:
            cmd = [interpreter, str(script_path)]
        else:
            # Assume script is executable
            cmd = [str(script_path)]

        # Prepare input
        stdin_data = None
        if input_data:
            stdin_data = json.dumps(input_data).encode('utf-8')

        timed_out = False
        process = None

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(skill_root)
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=stdin_data),
                    timeout=effective_timeout
                )
            except asyncio.TimeoutError:
                timed_out = True
                process.kill()
                await process.wait()
                stdout, stderr = b'', b'Execution timed out'

            exit_code = process.returncode or 0

            # Decode output
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            # Truncate if needed
            if len(stdout_str) > self.max_output_size:
                stdout_str = stdout_str[:self.max_output_size] + '\n... (output truncated)'
            if len(stderr_str) > self.max_output_size:
                stderr_str = stderr_str[:self.max_output_size] + '\n... (output truncated)'

            # Try to parse JSON result, otherwise use raw stdout
            result = stdout_str
            try:
                if stdout_str.strip():
                    result = json.loads(stdout_str)
            except json.JSONDecodeError:
                pass  # Keep raw string

            return ScriptExecutionResult(
                success=(exit_code == 0) and not timed_out,
                result=result,
                error=stderr_str if exit_code != 0 or timed_out else None,
                execution_time=time.time() - start_time,
                mode_used=ExecutionMode.SUBPROCESS,
                exit_code=exit_code,
                stdout=stdout_str,
                stderr=stderr_str,
                timed_out=timed_out
            )

        except Exception as e:
            return ScriptExecutionResult(
                success=False,
                result=None,
                error=f"Subprocess execution failed: {str(e)}",
                execution_time=time.time() - start_time,
                mode_used=ExecutionMode.SUBPROCESS
            )

    def _get_interpreter(self, script_path: Path) -> Optional[str]:
        """
        Get interpreter for script based on extension.

        Args:
            script_path: Path to the script

        Returns:
            Interpreter command or None if script should be run directly
        """
        return self.INTERPRETERS.get(script_path.suffix)

