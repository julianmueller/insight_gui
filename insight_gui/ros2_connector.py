# =============================================================================
# ros2_connector.py
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

from typing import Callable
import time

import rclpy
from rclpy.node import Node
from rclpy.publisher import Publisher, MsgType
from rclpy.subscription import Subscription
from rclpy.service import Service, SrvType, SrvTypeRequest, SrvTypeResponse
from rclpy.timer import Timer
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib, Gio


class ActionGoalHandle:
    """Wrapper for action goal handle with callbacks."""

    def __init__(self, goal_handle, feedback_callback=None, result_callback=None):
        self.goal_handle = goal_handle
        self.feedback_callback = feedback_callback
        self.result_callback = result_callback
        self.is_active = True

    def cancel(self):
        """Cancel the action goal."""
        if self.is_active and self.goal_handle:
            cancel_future = self.goal_handle.cancel_goal_async()
            self.is_active = False
            return cancel_future
        return None


class ROS2Connector:
    def __init__(self, application):
        super().__init__()
        self.app = application

        self.node: Node = None
        self.thread: GLib.Thread = None
        self.is_running = False
        self.start_time = None
        self.action_clients = {}  # Store action clients
        self.active_goals = {}  # Store active goal handles

        rclpy.init(args=None)

    def start_node(self, node_name: str = "insight_gui", *args, **kwargs):
        if self.is_running:
            return

        print(f"Starting ROS2 Node with name '{node_name}'")
        self.node = Node(node_name=node_name)
        self.start_time = self.node.get_clock().now()
        self.thread = GLib.Thread.new("ros2-thread", self.spin, None)
        self.is_running = True
        self.app.lookup_action("ros2-node-is-running").set_state(GLib.Variant.new_boolean(True))

    def stop_node(self):
        if not self.is_running:
            return

        self.is_running = False
        print(f"Stopping ROS2 Node with name '{self.node.get_name()}'")

        # Cancel all active goals
        for goal_id, goal_handle in self.active_goals.items():
            if goal_handle.is_active:
                goal_handle.cancel()

        # Destroy action clients
        for client in self.action_clients.values():
            client.destroy()
        self.action_clients.clear()
        self.active_goals.clear()

        if self.thread:
            self.thread.join()
            self.thread = None
        self.node.destroy_node()
        self.node = None
        self.app.lookup_action("ros2-node-is-running").set_state(GLib.Variant.new_boolean(False))

    def spin(self, *args, **kwargs):
        try:
            while rclpy.ok() and self.is_running:
                rclpy.spin_once(self.node, timeout_sec=0.1)
            return True  # Keep the timeout function/thread active

        except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
            print("CTRL+C detected. Shutting down ROS2 Node.")

        finally:
            # self.shutdown()
            self.is_running = False

        return False

    def on_node_state_changed(self, action: Gio.Action, value: GLib.Variant):
        action.set_state(GLib.Variant.new_boolean(self.is_running))

    def add_publisher(self, msg_type: MsgType, topic_name: str, queue_size: int = 10) -> Publisher:
        return self.node.create_publisher(msg_type, topic_name, queue_size)

    def destroy_publisher(self, pub: Publisher) -> bool:
        if not self.node:
            return

        if pub in list(self.node.publishers):
            return self.node.destroy_publisher(pub)
        else:
            raise RuntimeError("Publisher cannot be destroyed")
            return False

    def add_timer_callback(self, period: float, callback: Callable) -> Timer:
        return self.node.create_timer(period, callback)

    def add_subsciption(self, msg_type: MsgType, topic_name: str, callback: Callable) -> Subscription:
        return self.node.create_subscription(msg_type, topic_name, callback, 10)

    def destroy_subscription(self, sub: Subscription) -> bool:
        if not self.node:
            return

        if sub in list(self.node.subscriptions):
            return self.node.destroy_subscription(sub)
        else:
            raise RuntimeError("Subscription cannot be destroyed")
            return False

    # TODO this needs some refactoring and threading
    # from ros2service.verb.call import requester  # could also be used for that
    def call_service(
        self, srv_type: SrvType, srv_name: str, request: SrvTypeRequest, timeout_sec: int = -1
    ) -> SrvTypeResponse:
        if not self.is_running:
            return

        client = self.node.create_client(srv_type, srv_name)

        if not client.service_is_ready():
            client.wait_for_service(timeout_sec=2)

        future = client.call_async(request)
        # rclpy.spin_until_future_complete(self.node, future, timeout_sec=timeout_sec)
        start = time.monotonic()
        while not future.done():
            rclpy.spin_once(self.node, timeout_sec=0.01)
            if timeout_sec > 0 and (time.monotonic() - start) > timeout_sec:
                raise TimeoutError(f"Timeout while waiting for response from '{srv_name}'.")

        if future.result():
            return future.result()
        else:
            raise RuntimeError(f"Service call failed: {future.exception()}")

    def send_action_goal(
        self,
        action_type,
        action_name: str,
        goal,
        feedback_callback: Callable = None,
        result_callback: Callable = None,
        timeout_sec: int = 10,
    ) -> str:
        """
        Send an action goal and return a goal ID for tracking.

        Args:
            action_type: The action type class
            action_name: Name of the action server
            goal: The goal message
            feedback_callback: Called when feedback is received
            result_callback: Called when result is received
            timeout_sec: Timeout for waiting for action server

        Returns:
            goal_id: Unique identifier for tracking this goal
        """
        if not self.is_running:
            raise RuntimeError("ROS2 node is not running")

        # Create or get action client
        client_key = f"{action_name}_{action_type.__name__}"
        if client_key not in self.action_clients:
            self.action_clients[client_key] = ActionClient(self.node, action_type, action_name)

        action_client = self.action_clients[client_key]

        # Wait for action server
        if not action_client.wait_for_server(timeout_sec=timeout_sec):
            raise TimeoutError(f"Action server '{action_name}' not available after {timeout_sec} seconds")

        # Create goal request
        goal_msg = action_type.Goal()
        goal_msg = goal  # Assume goal is already the correct type

        # Send goal
        send_goal_future = action_client.send_goal_async(goal_msg, feedback_callback=feedback_callback)

        # Wait for goal acceptance
        start = time.monotonic()
        while not send_goal_future.done():
            rclpy.spin_once(self.node, timeout_sec=0.01)
            if timeout_sec > 0 and (time.monotonic() - start) > timeout_sec:
                raise TimeoutError(f"Timeout while waiting for goal acceptance from '{action_name}'.")

        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            raise RuntimeError(f"Goal was rejected by action server '{action_name}'")

        # Generate unique goal ID
        goal_id = f"{action_name}_{int(time.time() * 1000)}"

        # Store goal handle
        action_goal_handle = ActionGoalHandle(goal_handle, feedback_callback, result_callback)
        self.active_goals[goal_id] = action_goal_handle

        # Get result asynchronously
        get_result_future = goal_handle.get_result_async()

        def handle_result():
            """Handle the result when it's available."""
            start = time.monotonic()
            while not get_result_future.done():
                rclpy.spin_once(self.node, timeout_sec=0.01)
                if not self.is_running:
                    return
                # No timeout here - let the action run to completion

            result = get_result_future.result()
            action_goal_handle.is_active = False

            if result_callback:
                result_callback(result.result, result.status)

            # Clean up
            if goal_id in self.active_goals:
                del self.active_goals[goal_id]

        # Start result handling in a separate thread
        import threading

        result_thread = threading.Thread(target=handle_result, daemon=True)
        result_thread.start()

        return goal_id

    def cancel_action_goal(self, goal_id: str) -> bool:
        """Cancel an active action goal."""
        if goal_id in self.active_goals:
            goal_handle = self.active_goals[goal_id]
            cancel_future = goal_handle.cancel()
            if cancel_future:
                # Wait for cancellation
                start = time.monotonic()
                while not cancel_future.done():
                    rclpy.spin_once(self.node, timeout_sec=0.01)
                    if (time.monotonic() - start) > 5.0:  # 5 second timeout
                        break
                return True
        return False

    def get_action_goal_status(self, goal_id: str) -> int:
        """Get the status of an action goal."""
        if goal_id in self.active_goals:
            goal_handle = self.active_goals[goal_id]
            if goal_handle.goal_handle:
                return goal_handle.goal_handle.status
        return GoalStatus.STATUS_UNKNOWN

    def shutdown(self):
        for sub in list(self.node.subscriptions):
            self.node.destroy_subscription(sub)

        # self.is_running = False
        self.stop_node()
        # rclpy.shutdown()
        print("Shutting down ROS2 Node.")

    # TODO implement all the "get_available_xyz" from ros here and then call this from the pages, to make it consistent
