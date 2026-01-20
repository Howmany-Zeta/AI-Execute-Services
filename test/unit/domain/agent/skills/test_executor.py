"""
Unit tests for SkillScriptExecutor.
"""

import pytest
from pathlib import Path
import tempfile
import os

from aiecs.domain.agent.skills.executor import (
    ExecutionMode,
    ScriptExecutionResult,
    SkillScriptExecutor,
)


@pytest.fixture
def temp_skill_dir():
    """Create a temporary skill directory with test scripts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_path = Path(tmpdir) / "test-skill"
        skill_path.mkdir()
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        
        # Create a sync Python script
        sync_script = scripts_dir / "sync_script.py"
        sync_script.write_text('''
def execute(input_data):
    """Sync entry point."""
    name = input_data.get("name", "World")
    return {"greeting": f"Hello, {name}!"}
''')
        
        # Create an async Python script
        async_script = scripts_dir / "async_script.py"
        async_script.write_text('''
import asyncio

async def execute(input_data):
    """Async entry point."""
    await asyncio.sleep(0.01)
    value = input_data.get("value", 0)
    return {"result": value * 2}
''')
        
        # Create a script with alternative entry point
        main_script = scripts_dir / "main_script.py"
        main_script.write_text('''
def main(input_data):
    """Alternative entry point."""
    return {"entry": "main"}
''')
        
        # Create a script with 'run' entry point
        run_script = scripts_dir / "run_script.py"
        run_script.write_text('''
def run(input_data):
    """Run entry point."""
    return {"entry": "run"}
''')
        
        # Create a script that raises an error
        error_script = scripts_dir / "error_script.py"
        error_script.write_text('''
def execute(input_data):
    raise ValueError("Test error")
''')
        
        # Create a script without entry point
        no_entry_script = scripts_dir / "no_entry.py"
        no_entry_script.write_text('''
# No entry point
x = 42
''')
        
        # Create a slow script for timeout testing
        slow_script = scripts_dir / "slow_script.py"
        slow_script.write_text('''
import time

def execute(input_data):
    time.sleep(10)  # Sleep for 10 seconds
    return {"done": True}
''')
        
        # Create a shell script
        shell_script = scripts_dir / "test.sh"
        shell_script.write_text('#!/bin/bash\necho "{"result": "shell"}"\n')
        os.chmod(shell_script, 0o755)
        
        # Create a Python subprocess script
        subprocess_py = scripts_dir / "subprocess_script.py"
        subprocess_py.write_text('''#!/usr/bin/env python3
import json
import sys

data = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}
result = {"received": data, "processed": True}
print(json.dumps(result))
''')
        os.chmod(subprocess_py, 0o755)
        
        # Create a script that accesses __skill_root__
        root_access_script = scripts_dir / "root_access.py"
        root_access_script.write_text('''
# Access __skill_root__ set by executor at module level
_skill_root = None

def execute(input_data):
    global _skill_root
    # The __skill_root__ is set on the module before exec_module
    # We can access it via globals()
    skill_root = globals().get('__skill_root__')
    return {"skill_root": str(skill_root) if skill_root else None}
''')
        
        yield skill_path


@pytest.fixture
def executor():
    """Create a SkillScriptExecutor instance."""
    return SkillScriptExecutor(default_timeout=5, max_timeout=30)


class TestExecutionMode:
    """Tests for ExecutionMode enum."""

    def test_enum_values(self):
        """Test ExecutionMode enum values."""
        assert ExecutionMode.NATIVE.value == "native"
        assert ExecutionMode.SUBPROCESS.value == "subprocess"
        assert ExecutionMode.AUTO.value == "auto"


class TestScriptExecutionResult:
    """Tests for ScriptExecutionResult dataclass."""

    def test_success_result(self):
        """Test successful result."""
        result = ScriptExecutionResult(
            success=True,
            result={"data": "test"},
            execution_time=0.5,
            mode_used=ExecutionMode.NATIVE
        )
        assert result.success is True
        assert result.result == {"data": "test"}
        assert result.error is None

    def test_blocking_error(self):
        """Test blocking error detection."""
        result = ScriptExecutionResult(
            success=False,
            result=None,
            exit_code=2,
            mode_used=ExecutionMode.SUBPROCESS
        )
        assert result.blocking_error is True

    def test_non_blocking_error(self):
        """Test non-blocking error."""
        result = ScriptExecutionResult(
            success=False,
            result=None,
            exit_code=1,
            mode_used=ExecutionMode.SUBPROCESS
        )
        assert result.blocking_error is False


class TestModeResolution:
    """Tests for mode resolution logic."""

    def test_auto_resolves_to_native_for_python(self, executor, temp_skill_dir):
        """Test AUTO mode resolves to NATIVE for .py files."""
        script_path = temp_skill_dir / "scripts" / "sync_script.py"
        mode = executor._resolve_mode(script_path, ExecutionMode.AUTO)
        assert mode == ExecutionMode.NATIVE

    def test_auto_resolves_to_subprocess_for_shell(self, executor, temp_skill_dir):
        """Test AUTO mode resolves to SUBPROCESS for .sh files."""
        script_path = temp_skill_dir / "scripts" / "test.sh"
        mode = executor._resolve_mode(script_path, ExecutionMode.AUTO)
        assert mode == ExecutionMode.SUBPROCESS

    def test_explicit_mode_preserved(self, executor, temp_skill_dir):
        """Test explicit mode is not changed."""
        script_path = temp_skill_dir / "scripts" / "sync_script.py"

        mode = executor._resolve_mode(script_path, ExecutionMode.SUBPROCESS)
        assert mode == ExecutionMode.SUBPROCESS

        mode = executor._resolve_mode(script_path, ExecutionMode.NATIVE)
        assert mode == ExecutionMode.NATIVE


class TestNativeExecution:
    """Tests for native mode execution."""

    @pytest.mark.asyncio
    async def test_sync_script(self, executor, temp_skill_dir):
        """Test synchronous script execution."""
        script_path = temp_skill_dir / "scripts" / "sync_script.py"

        result = await executor.execute(
            script_path=script_path,
            skill_root=temp_skill_dir,
            input_data={"name": "Test"},
            mode=ExecutionMode.NATIVE
        )

        assert result.success is True
        assert result.result == {"greeting": "Hello, Test!"}
        assert result.mode_used == ExecutionMode.NATIVE
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_async_script(self, executor, temp_skill_dir):
        """Test asynchronous script execution."""
        script_path = temp_skill_dir / "scripts" / "async_script.py"

        result = await executor.execute(
            script_path=script_path,
            skill_root=temp_skill_dir,
            input_data={"value": 21},
            mode=ExecutionMode.NATIVE
        )

        assert result.success is True
        assert result.result == {"result": 42}
        assert result.mode_used == ExecutionMode.NATIVE

    @pytest.mark.asyncio
    async def test_main_entry_point(self, executor, temp_skill_dir):
        """Test script with main() entry point."""
        script_path = temp_skill_dir / "scripts" / "main_script.py"

        result = await executor.execute(
            script_path=script_path,
            skill_root=temp_skill_dir,
            mode=ExecutionMode.NATIVE
        )

        assert result.success is True
        assert result.result == {"entry": "main"}

    @pytest.mark.asyncio
    async def test_run_entry_point(self, executor, temp_skill_dir):
        """Test script with run() entry point."""
        script_path = temp_skill_dir / "scripts" / "run_script.py"

        result = await executor.execute(
            script_path=script_path,
            skill_root=temp_skill_dir,
            mode=ExecutionMode.NATIVE
        )

        assert result.success is True
        assert result.result == {"entry": "run"}

    @pytest.mark.asyncio
    async def test_missing_entry_point(self, executor, temp_skill_dir):
        """Test script without entry point."""
        script_path = temp_skill_dir / "scripts" / "no_entry.py"

        result = await executor.execute(
            script_path=script_path,
            skill_root=temp_skill_dir,
            mode=ExecutionMode.NATIVE
        )

        assert result.success is False
        assert "missing entry point" in result.error

    @pytest.mark.asyncio
    async def test_script_error(self, executor, temp_skill_dir):
        """Test script that raises an exception."""
        script_path = temp_skill_dir / "scripts" / "error_script.py"

        result = await executor.execute(
            script_path=script_path,
            skill_root=temp_skill_dir,
            mode=ExecutionMode.NATIVE
        )

        assert result.success is False
        assert "ValueError" in result.error
        assert "Test error" in result.error

    @pytest.mark.asyncio
    async def test_skill_root_accessible(self, executor, temp_skill_dir):
        """Test that __skill_root__ is set on module."""
        script_path = temp_skill_dir / "scripts" / "root_access.py"

        result = await executor.execute(
            script_path=script_path,
            skill_root=temp_skill_dir,
            mode=ExecutionMode.NATIVE
        )

        assert result.success is True
        assert str(temp_skill_dir) in result.result["skill_root"]

    @pytest.mark.asyncio
    async def test_timeout(self, temp_skill_dir):
        """Test timeout enforcement."""
        executor = SkillScriptExecutor(default_timeout=1, max_timeout=2)
        script_path = temp_skill_dir / "scripts" / "slow_script.py"

        result = await executor.execute(
            script_path=script_path,
            skill_root=temp_skill_dir,
            timeout=1,
            mode=ExecutionMode.NATIVE
        )

        assert result.success is False
        assert result.timed_out is True
        assert "timed out" in result.error


class TestSubprocessExecution:
    """Tests for subprocess mode execution."""

    @pytest.mark.asyncio
    async def test_shell_script(self, executor, temp_skill_dir):
        """Test shell script execution."""
        script_path = temp_skill_dir / "scripts" / "test.sh"

        result = await executor.execute(
            script_path=script_path,
            skill_root=temp_skill_dir,
            mode=ExecutionMode.SUBPROCESS
        )

        assert result.success is True
        assert result.mode_used == ExecutionMode.SUBPROCESS
        assert result.exit_code == 0
        assert result.stdout is not None

    @pytest.mark.asyncio
    async def test_python_subprocess_with_json(self, executor, temp_skill_dir):
        """Test Python script in subprocess mode with JSON I/O."""
        script_path = temp_skill_dir / "scripts" / "subprocess_script.py"

        result = await executor.execute(
            script_path=script_path,
            skill_root=temp_skill_dir,
            input_data={"test": "data"},
            mode=ExecutionMode.SUBPROCESS
        )

        assert result.success is True
        assert result.mode_used == ExecutionMode.SUBPROCESS
        assert result.result["processed"] is True
        assert result.result["received"] == {"test": "data"}

    @pytest.mark.asyncio
    async def test_env_vars(self, executor, temp_skill_dir):
        """Test environment variables are passed."""
        # Create a script that checks env vars
        env_script = temp_skill_dir / "scripts" / "env_check.py"
        env_script.write_text('''#!/usr/bin/env python3
import os
import json
print(json.dumps({
    "SKILL_ROOT": os.environ.get("SKILL_ROOT"),
    "AIECS_SCRIPT_MODE": os.environ.get("AIECS_SCRIPT_MODE"),
    "CUSTOM_VAR": os.environ.get("CUSTOM_VAR")
}))
''')
        os.chmod(env_script, 0o755)

        result = await executor.execute(
            script_path=env_script,
            skill_root=temp_skill_dir,
            env_vars={"CUSTOM_VAR": "test_value"},
            mode=ExecutionMode.SUBPROCESS
        )

        assert result.success is True
        assert result.result["SKILL_ROOT"] == str(temp_skill_dir)
        assert result.result["AIECS_SCRIPT_MODE"] == "subprocess"
        assert result.result["CUSTOM_VAR"] == "test_value"


class TestSecurityValidations:
    """Tests for security validations."""

    @pytest.mark.asyncio
    async def test_script_not_found(self, executor, temp_skill_dir):
        """Test error when script doesn't exist."""
        script_path = temp_skill_dir / "scripts" / "nonexistent.py"

        result = await executor.execute(
            script_path=script_path,
            skill_root=temp_skill_dir
        )

        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_path_outside_skill_dir(self, executor, temp_skill_dir):
        """Test error when script is outside skill directory."""
        # Create a script outside skill dir
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(b'def execute(d): return {}')
            outside_script = Path(f.name)

        try:
            result = await executor.execute(
                script_path=outside_script,
                skill_root=temp_skill_dir
            )

            assert result.success is False
            assert "must be within skill directory" in result.error
        finally:
            outside_script.unlink()


class TestInterpreterDetection:
    """Tests for interpreter detection."""

    def test_python_interpreter(self, executor):
        """Test Python interpreter detection."""
        assert executor._get_interpreter(Path("test.py")) == "python3"

    def test_shell_interpreter(self, executor):
        """Test shell interpreter detection."""
        assert executor._get_interpreter(Path("test.sh")) == "bash"

    def test_node_interpreter(self, executor):
        """Test Node.js interpreter detection."""
        assert executor._get_interpreter(Path("test.js")) == "node"

    def test_ruby_interpreter(self, executor):
        """Test Ruby interpreter detection."""
        assert executor._get_interpreter(Path("test.rb")) == "ruby"

    def test_unknown_extension(self, executor):
        """Test unknown extension returns None."""
        assert executor._get_interpreter(Path("test.xyz")) is None

