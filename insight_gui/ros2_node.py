from typing import Callable, Type

# ros2 specific imports
import rclpy
from rclpy.node import Node

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib


class ROS2CommunicationNode:
    def __init__(self):
        super().__init__()

        # init ros2 node thread, and start it
        self.node: Node = None
        self.thread: GLib.Thread = None
        self.is_running = False

    # @property
    # def is_running(self) -> bool:
    #     # return self.spin_event.is_set()
    #     return True

    def start_node(self, node_name: str = "insight_gui", *args, **kwargs):
        if not self.is_running:
            print(f"Starting ROS2 Node with name '{node_name}'")
            rclpy.init(args=None)
            self.node = Node(node_name=node_name)
            self.thread = GLib.Thread.new("ros2-thread", self.spin, None)
            self.is_running = True

    def stop_node(self):
        if self.is_running:
            print(f"Stopping ROS2 Node with name '{self.node.get_name()}'")
            # self.spin_event.clear()
            self.is_running = False
            if self.thread:
                self.thread.join()
                self.thread = None
            self.node.destroy_node()
            self.node = None

    def spin(self, *args, **kwargs):
        try:
            while rclpy.ok() and self.is_running:  # TODO this somehow causes a problems
                # if self.spin_event.is_set():
                rclpy.spin_once(self.node, timeout_sec=0.5)
            return True  # Keep the timeout function active

        except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
            print("CTRL+C detected. Shutting down ROS2 Node.")

        finally:
            self.shutdown()
            # self.spin_event.clear()
        return False

    def add_subsciption(self, msg_type: Type, topic_name: str, callback: Callable):
        print("adding subsciption")
        sub = self.node.create_subscription(msg_type, topic_name, callback, 10)
        return sub

    def shutdown(self):
        self.stop_node()
        rclpy.shutdown()
        print("Shutting down ROS2 Node.")
