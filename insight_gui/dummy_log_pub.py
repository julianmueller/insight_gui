# =============================================================================
# dummy_log_pub.py
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

import random
import rclpy
from rclpy.node import Node


class RandomLoggerNode(Node):
    """A ROS 2 node that logs random messages at random severity levels at a fixed rate."""

    def __init__(self):
        super().__init__("random_logger_node")
        self.get_logger().set_level(rclpy.logging.LoggingSeverity.DEBUG)

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
            self.get_logger().debug(f"{message}")
        elif log_level == "info":
            self.get_logger().info(f"{message}")
        elif log_level == "warn":
            self.get_logger().warn(f"{message}")
        elif log_level == "error":
            self.get_logger().error(f"{message}")
        elif log_level == "fatal":
            self.get_logger().fatal(f"{message}")


def main(args=None):
    rclpy.init(args=args)
    node = RandomLoggerNode()
    rclpy.spin(node)  # Keep the node running
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
