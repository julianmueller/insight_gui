import threading
from typing import Callable, Type

# ros2 specific imports
import rclpy
from rclpy.node import Node


class ROS2CommunicationNode:
    def __init__(self):
        super().__init__()
        rclpy.init(args=None)

        # init ros2 node thread, and start it
        self.node = None
        self.thread = threading.Thread(target=self.spin)
        self.spin_event = threading.Event()
        self.thread.start()

    @property
    def is_running(self) -> bool:
        return self.spin_event.is_set()

    def start_node(self, node_name: str = "insight_gui", *args, **kwargs):
        if not self.is_running:
            print(f"Starting ROS2 Node with name '{node_name}'")

            self.node = Node(node_name=node_name)
            self.spin_event.set()

    def stop_node(self):
        if self.is_running:
            print(f"Stopping ROS2 Node with name '{self.node.get_name()}'")

            self.spin_event.clear()
            self.node.destroy_node()
            self.node = None

    def spin(self):
        try:
            while rclpy.ok():  # TODO this somehow causes a problems
                if self.spin_event.is_set():
                    rclpy.spin_once(self.node, timeout_sec=0.5)
            return True  # Keep the timeout function active

        except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
            print("CTRL+C detected. Shutting down ROS2 Node.")

        finally:
            self.spin_event.clear()

    def add_subsciption(self, msg_type: Type, topic_name: str, callback: Callable):
        print("adding subsciption")
        sub = self.node.create_subscription(msg_type, topic_name, callback, 10)
        return sub

    def shutdown(self):
        self.stop_node()
        rclpy.shutdown()
        self.thread.join()
        print("Shutting down ROS2 Node.")
