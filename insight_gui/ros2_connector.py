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


import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib, Gio


class ROS2Connector:
    def __init__(self, application):
        super().__init__()
        self.app = application

        self.node: Node = None
        self.thread: GLib.Thread = None
        self.is_running = False
        self.start_time = None

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

    def shutdown(self):
        for sub in list(self.node.subscriptions):
            self.node.destroy_subscription(sub)

        # self.is_running = False
        self.stop_node()
        # rclpy.shutdown()
        print("Shutting down ROS2 Node.")

    # TODO implement all the "get_available_xyz" from ros here and then call this from the pages, to make it consistent
