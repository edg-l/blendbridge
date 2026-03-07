"""Queue-based script executor that runs on Blender's main thread via bpy.app.timers."""

import io
import queue
import sys
import traceback

import bpy

_request_queue = queue.Queue()
_timer_registered = False


class ScriptResult:
    __slots__ = ("success", "output", "error", "event")

    def __init__(self):
        self.success = False
        self.output = ""
        self.error = None
        self.event = None


def submit(script: str, timeout: float = 30.0) -> ScriptResult:
    """Submit a script for execution on the main thread. Blocks until complete."""
    import threading

    result = ScriptResult()
    result.event = threading.Event()
    _request_queue.put((script, result))
    result.event.wait(timeout=timeout)

    if not result.event.is_set():
        result.success = False
        result.error = f"Script execution timed out after {timeout}s"

    return result


def _execute_one(script: str, result: ScriptResult):
    """Execute a single script, capturing output and errors."""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    old_stdout, old_stderr = sys.stdout, sys.stderr

    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        namespace = {"bpy": bpy, "__name__": "__main__"}
        exec(compile(script, "<blendbridge>", "exec"), namespace)

        result.success = True
        result.output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
        if stderr_output:
            result.output += stderr_output
    except Exception:
        result.success = False
        result.output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
        if stderr_output:
            result.output += stderr_output
        result.error = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        result.event.set()


def _timer_callback():
    """Called by bpy.app.timers on the main thread. Processes queued scripts."""
    try:
        script, result = _request_queue.get_nowait()
        _execute_one(script, result)
    except queue.Empty:
        pass
    return 0.05  # re-run every 50ms


def start():
    global _timer_registered
    if not _timer_registered:
        bpy.app.timers.register(_timer_callback, persistent=True)
        _timer_registered = True


def stop():
    global _timer_registered
    if _timer_registered:
        try:
            bpy.app.timers.unregister(_timer_callback)
        except ValueError:
            pass
        _timer_registered = False
