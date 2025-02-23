import random
import rclpy
from rclpy.node import Node


class RandomLoggerNode(Node):
    """A ROS 2 node that logs random messages at random severity levels at a fixed rate."""

    def __init__(self):
        super().__init__("random_logger_node")

        self.log_messages = [
            "System is running smoothly.",
            "Unexpected behavior detected!",
            "Trying to reconnect to the server...",
            "Low memory warning!",
            "Critical system failure!",
            "Processing data packets...",
            "Battery level is low.",
            "Sensor readings out of range.",
            "Initializing sequence complete.",
            "All systems nominal.",
        ]

        self.log_levels = ["debug", "info", "warn", "error", "fatal"]
        self.timer_period = 0.5  # Log every 2 seconds
        self.timer = self.create_timer(self.timer_period, self.log_random_message)

    def log_random_message(self):
        """Logs a random message at a random severity level."""
        message = random.choice(self.log_messages)
        log_level = random.choice(self.log_levels)

        if log_level == "debug":
            self.get_logger().debug(f"[DEBUG] {message}")
        elif log_level == "info":
            self.get_logger().info(f"[INFO] {message}")
        elif log_level == "warn":
            self.get_logger().warn(f"[WARN] {message}")
        elif log_level == "error":
            self.get_logger().error(f"[ERROR] {message}")
        elif log_level == "fatal":
            self.get_logger().fatal(f"[FATAL] {message}")


def main(args=None):
    rclpy.init(args=args)
    node = RandomLoggerNode()
    rclpy.spin(node)  # Keep the node running
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
