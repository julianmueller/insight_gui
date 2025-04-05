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

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np


class DummyImagePublisher(Node):
    """
    Simple ROS2 node that publishes a random 640x480 BGR8 image
    to the '/dummy_image' topic at ~10 Hz.
    """

    def __init__(self):
        super().__init__("dummy_image_publisher")
        self.publisher_ = self.create_publisher(Image, "/dummy_image", 10)
        self.timer = self.create_timer(0.05, self.timer_callback)  # ~10 Hz
        self.bridge = CvBridge()
        self.frame_count = 0

    def timer_callback(self):
        # Generate a random 640x480 BGR8 image (uint8)
        height, width = 480, 640
        random_image = np.random.randint(low=0, high=256, size=(height, width, 3), dtype=np.uint8)

        # Convert to a ROS2 Image message (BGR8 encoding)
        msg = self.bridge.cv2_to_imgmsg(random_image, encoding="bgr8")
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "dummy_frame"

        self.publisher_.publish(msg)
        self.get_logger().info(f"Published dummy image {self.frame_count}")
        self.frame_count += 1


def main(args=None):
    rclpy.init(args=args)
    node = DummyImagePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
