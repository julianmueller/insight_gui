# =============================================================================
# dummy_img_pub.py
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

import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class DummyPublisher(Node):
    def __init__(self, name, topic):
        super().__init__(name)
        self.publisher = self.create_publisher(String, topic, 10)
        self.timer = self.create_timer(1.0, self.publish_msg)

    def publish_msg(self):
        msg = String()
        msg.data = f"Hello from {self.get_name()}"
        self.publisher.publish(msg)


class DummySubscriber(Node):
    def __init__(self, name, topics):
        super().__init__(name)
        self.subs = []
        for topic in topics:
            self.subs.append(self.create_subscription(String, topic, self.cb, 10))

    def cb(self, msg):
        self.get_logger().info(f"[{self.get_name()}] received: {msg.data}")


def main():
    rclpy.init()

    # Sensor Nodes → /scan_raw
    sensor_1 = DummyPublisher("sensor_1", "/scan_raw")
    sensor_2 = DummyPublisher("sensor_2", "/scan_raw")

    # Filters listen to /scan_raw → publish to /scan_filtered
    filter_1 = DummySubscriber("filter_1", ["/scan_raw"])
    filter_1.publisher = filter_1.create_publisher(String, "/scan_filtered", 10)
    filter_1.timer = filter_1.create_timer(2.0, lambda: filter_1.publisher.publish(String(data="filtered by 1")))

    filter_2 = DummySubscriber("filter_2", ["/scan_raw"])
    filter_2.publisher = filter_2.create_publisher(String, "/scan_filtered", 10)
    filter_2.timer = filter_2.create_timer(3.0, lambda: filter_2.publisher.publish(String(data="filtered by 2")))

    # Planners listen to /scan_filtered
    planner_1 = DummySubscriber("planner_1", ["/scan_filtered"])
    planner_2 = DummySubscriber("planner_2", ["/scan_filtered"])

    # Visualizer listens to /scan_filtered
    visualizer = DummySubscriber("visualizer", ["/scan_filtered"])

    nodes = [sensor_1, sensor_2, filter_1, filter_2, planner_1, planner_2, visualizer]

    # Spin all nodes in one executor
    executor = rclpy.executors.MultiThreadedExecutor()
    for node in nodes:
        executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        for node in nodes:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
