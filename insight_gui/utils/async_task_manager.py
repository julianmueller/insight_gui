# =============================================================================
# async_task_manager.py
#
# This file is part of https://github.com/julianmueller/insight_gui
# Copyright (C) 2025 Julian Müller
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later
# =============================================================================

import threading
import time
from typing import Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum
import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncTask:
    """Represents an async task with callbacks."""

    task_id: str
    background_func: Callable
    success_callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    progress_callback: Optional[Callable] = None
    args: tuple = ()
    kwargs: dict = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Exception = None

    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}


class AsyncTaskManager:
    """
    Centralized manager for handling async operations with proper UI updates.

    This class provides a clean interface for running background tasks while
    ensuring UI updates happen on the main thread via GLib.idle_add.
    """

    def __init__(self):
        self._tasks = {}
        self._running_tasks = set()
        self._lock = threading.Lock()

    def run_task(
        self,
        task_id: str,
        background_func: Callable,
        success_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None,
        *args,
        **kwargs,
    ) -> str:
        """
        Run an async task with proper UI callback handling.

        Args:
            task_id: Unique identifier for the task
            background_func: Function to run in background thread
            success_callback: Called on main thread when task succeeds
            error_callback: Called on main thread when task fails
            progress_callback: Called on main thread for progress updates
            *args, **kwargs: Arguments passed to background_func

        Returns:
            task_id for tracking the task
        """

        # Cancel existing task with same ID
        self.cancel_task(task_id)

        task = AsyncTask(
            task_id=task_id,
            background_func=background_func,
            success_callback=success_callback,
            error_callback=error_callback,
            progress_callback=progress_callback,
            args=args,
            kwargs=kwargs,
        )

        with self._lock:
            self._tasks[task_id] = task
            self._running_tasks.add(task_id)

        # Start the background thread
        thread = threading.Thread(target=self._run_background_task, args=(task,), daemon=True)
        thread.start()

        return task_id

    def _run_background_task(self, task: AsyncTask):
        """Run the background task and handle callbacks."""
        try:
            task.status = TaskStatus.RUNNING

            # Run the background function
            result = task.background_func(*task.args, **task.kwargs)

            # Check if task was cancelled
            with self._lock:
                if task.task_id not in self._running_tasks:
                    return

            task.result = result
            task.status = TaskStatus.COMPLETED

            # Schedule success callback on main thread
            if task.success_callback:
                GLib.idle_add(self._handle_success, task)

        except Exception as e:
            task.error = e
            task.status = TaskStatus.FAILED

            # Schedule error callback on main thread
            if task.error_callback:
                GLib.idle_add(self._handle_error, task)

        finally:
            with self._lock:
                self._running_tasks.discard(task.task_id)

    def _handle_success(self, task: AsyncTask) -> bool:
        """Handle successful task completion on main thread."""
        try:
            task.success_callback(task.result)
        except Exception as e:
            print(f"Error in success callback for task {task.task_id}: {e}")
        return False  # Don't repeat

    def _handle_error(self, task: AsyncTask) -> bool:
        """Handle task error on main thread."""
        try:
            task.error_callback(task.error)
        except Exception as e:
            print(f"Error in error callback for task {task.task_id}: {e}")
        return False  # Don't repeat

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        with self._lock:
            if task_id in self._running_tasks:
                self._running_tasks.remove(task_id)
                if task_id in self._tasks:
                    self._tasks[task_id].status = TaskStatus.CANCELLED
                return True
        return False

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a task."""
        with self._lock:
            task = self._tasks.get(task_id)
            return task.status if task else None

    def is_task_running(self, task_id: str) -> bool:
        """Check if a task is currently running."""
        with self._lock:
            return task_id in self._running_tasks


class UIUpdateBatcher:
    """
    Batches UI updates to prevent overwhelming the main thread.

    Useful for high-frequency updates like topic subscriptions.
    """

    def __init__(self, update_rate_hz: float = 30.0):
        self.update_rate_hz = update_rate_hz
        self.min_interval = 1.0 / update_rate_hz
        self._pending_updates = {}
        self._last_update_times = {}
        self._lock = threading.Lock()

    def schedule_update(self, update_id: str, update_func: Callable, *args, **kwargs):
        """
        Schedule a UI update, batching if called frequently.

        Args:
            update_id: Unique identifier for this type of update
            update_func: Function to call for the update
            *args, **kwargs: Arguments for update_func
        """
        current_time = time.time()

        with self._lock:
            last_update = self._last_update_times.get(update_id, 0)

            # Store the latest update
            self._pending_updates[update_id] = (update_func, args, kwargs)

            # If enough time has passed, schedule the update
            if current_time - last_update >= self.min_interval:
                self._last_update_times[update_id] = current_time
                GLib.idle_add(self._execute_update, update_id)

    def _execute_update(self, update_id: str) -> bool:
        """Execute the pending update on the main thread."""
        with self._lock:
            if update_id in self._pending_updates:
                update_func, args, kwargs = self._pending_updates.pop(update_id)
                try:
                    update_func(*args, **kwargs)
                except Exception as e:
                    print(f"Error in batched update {update_id}: {e}")
        return False  # Don't repeat


# Global instances
task_manager = AsyncTaskManager()
ui_batcher = UIUpdateBatcher()
