# =============================================================================
# background_worker.py
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

import concurrent.futures
import threading
import heapq
from dataclasses import dataclass, field
from functools import partial
from collections.abc import Callable


WORKER_PRIORITY_HIGH = 0
WORKER_PRIORITY_NORMAL = 10
WORKER_PRIORITY_LOW = 20


@dataclass(order=True)
class _WorkerItem:
    priority: int
    order: int
    func: Callable = field(compare=False)
    args: tuple = field(compare=False)
    kwargs: dict = field(compare=False)
    future: concurrent.futures.Future = field(compare=False)
    done_callback: Callable[[concurrent.futures.Future], None] | None = field(compare=False, default=None)
    running: bool = field(compare=False, default=False)
    cancelled: bool = field(compare=False, default=False)
    worker_future: concurrent.futures.Future | None = field(compare=False, default=None)


class BackgroundWorker:
    """Priority-aware worker pool for background tasks."""

    def __init__(self, max_workers: int = 2, thread_name_prefix: str = "insight-worker"):
        self._loop_ready = threading.Event()
        self._max_workers = max_workers
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._max_workers, thread_name_prefix=thread_name_prefix
        )
        self._queue: list[tuple[int, int, _WorkerItem]] = []
        self._lock = threading.Lock()
        self._counter = 0
        self._active_workers = 0
        self._work_items: dict[concurrent.futures.Future, _WorkerItem] = {}
        self._loop_ready.set()

    def shutdown(self, wait: bool = False, cancel_futures: bool = True) -> None:
        """Shutdown executor and clear queued work."""
        with self._lock:
            for item in list(self._work_items.values()):
                item.cancelled = True
                item.future.cancel()
                if item.worker_future and not item.worker_future.done():
                    item.worker_future.cancel()
            self._queue.clear()
            self._work_items.clear()
            self._active_workers = 0
        self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)

    def run_in_worker(
        self,
        func: Callable,
        *args,
        done_callback: Callable[[concurrent.futures.Future], None] | None = None,
        priority: int = WORKER_PRIORITY_NORMAL,
        **kwargs,
    ) -> concurrent.futures.Future:
        """
        Run a blocking callable on the worker pool.

        The optional ``done_callback`` receives the resulting Future and is
        executed in the worker thread context, so use GTK-safe handoff for UI.
        ``priority`` is lower-is-higher (0 is highest) and only affects queued tasks.
        """

        if not self._loop_ready.wait(timeout=1):
            raise RuntimeError("Background worker not ready")

        result_future: concurrent.futures.Future = concurrent.futures.Future()
        work_item = _WorkerItem(
            priority=int(priority),
            order=self._counter,
            func=func,
            args=args,
            kwargs=kwargs,
            future=result_future,
            done_callback=done_callback,
        )

        with self._lock:
            self._counter += 1
            heapq.heappush(self._queue, (work_item.priority, work_item.order, work_item))
            self._work_items[result_future] = work_item
            self._schedule_locked()

        result_future.add_done_callback(lambda fut, item=work_item: self._on_result_future_done(fut, item))
        return result_future

    def reprioritize_worker_future(self, fut: concurrent.futures.Future, priority: int) -> bool:
        """Lower or raise priority of a queued future if it has not started yet."""
        with self._lock:
            item = self._work_items.get(fut)
            if not item or item.running or item.cancelled or fut.cancelled():
                return False

            item.priority = int(priority)
            self._counter += 1
            heapq.heappush(self._queue, (item.priority, self._counter, item))
            self._schedule_locked()
            return True

    # Internal helpers -----------------------------------------------------
    def _schedule_locked(self) -> None:
        """Dispatch queued work respecting priority and available slots."""
        while self._active_workers < self._max_workers and self._queue:
            priority, _, item = heapq.heappop(self._queue)
            if item.cancelled or item.future.cancelled():
                continue
            if priority != item.priority or item.running:
                continue

            item.running = True
            self._active_workers += 1

            worker_future = self._executor.submit(partial(item.func, *item.args, **item.kwargs))
            item.worker_future = worker_future
            worker_future.add_done_callback(lambda wf, work_item=item: self._on_worker_done(wf, work_item))

    def _on_worker_done(self, worker_future: concurrent.futures.Future, work_item: _WorkerItem) -> None:
        try:
            if worker_future.cancelled() or work_item.future.cancelled() or work_item.cancelled:
                work_item.future.cancel()
            else:
                result = worker_future.result()
                if not work_item.future.cancelled():
                    work_item.future.set_result(result)
        except Exception as exc:
            if not work_item.future.cancelled():
                work_item.future.set_exception(exc)
        finally:
            if work_item.done_callback and not work_item.future.cancelled():
                try:
                    work_item.done_callback(work_item.future)
                except Exception as cb_exc:
                    print(f"Worker done_callback raised: {cb_exc}")
            with self._lock:
                work_item.running = False
                self._active_workers -= 1
                self._work_items.pop(work_item.future, None)
                self._schedule_locked()

    def _on_result_future_done(self, fut: concurrent.futures.Future, item: _WorkerItem) -> None:
        """Handle user-triggered cancellation on the result future."""
        if fut.cancelled():
            item.cancelled = True
            if item.worker_future and not item.worker_future.done():
                item.worker_future.cancel()
        with self._lock:
            self._work_items.pop(fut, None)
