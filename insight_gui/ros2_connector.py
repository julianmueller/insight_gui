# Copyright (C) 2025  Julian Müller

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Callable, Type

# ros2 specific imports
import rclpy
from rclpy.node import Node
from rclpy.service import SrvType, SrvTypeRequest, SrvTypeResponse

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib, Gio


class ROS2Connector:
    def __init__(self):
        super().__init__()
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
        """
        This callback is invoked when the action's state is requested to change.
        'value' is a GLib.Variant wrapping the new boolean state.
        """
        new_state = value.get_boolean()
        action.set_state(value)
        if new_state:
            self.start_node()
        else:
            self.stop_node()

    # TODO
    def add_subsciption(self, msg_type: Type, topic_name: str, callback: Callable):
        # print("adding subsciption")
        sub = self.node.create_subscription(msg_type, topic_name, callback, 10)
        return sub

    # TODO this needs some refactoring and threading
    # from ros2service.verb.call import requester  # could also be used for that
    def call_service(self, srv_name: str, srv_type: SrvType, request: SrvTypeRequest) -> SrvTypeResponse:
        if not self.is_running:
            return

        client = self.node.create_client(srv_type, srv_name)

        if not client.service_is_ready():
            print("waiting for service to become available...")
            client.wait_for_service()

        future = client.call_async(request)
        rclpy.spin_until_future_complete(self.node, future)
        if future.result() is not None:
            return future.result()
        else:
            raise RuntimeError("Exception while calling service: %r" % future.exception())

    def shutdown(self):
        # self.is_running = False
        self.stop_node()
        # rclpy.shutdown()
        print("Shutting down ROS2 Node.")
