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

from pathlib import Path
import cv2
from urllib.request import urlopen
import numpy as np

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ament_index_python import get_package_share_directory


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
        self.share_dir = Path(get_package_share_directory("insight_gui")) / "data"

    def timer_callback(self):
        # Generate a random 640x480 BGR8 image (uint8)
        # height, width = 480, 640
        # random_image = np.random.randint(low=0, high=256, size=(height, width, 3), dtype=np.uint8)
        # Load an image from file using OpenCV

        url_response = urlopen(
            "https://github.com/ros-infrastructure/artwork/blob/master/distributions/jazzy/JazzyJalisco-noborder.png?raw=true"
        )
        image = np.asarray(bytearray(url_response.read()), dtype=np.uint8)
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)  # The image object

        # Check if the image was loaded successfully
        if image is None:
            self.get_logger().error("Failed to load image. Please check the file path.")
            return

        # Resize the image to 640x480 if necessary
        image = cv2.resize(image, (640, 480))

        # Convert to a ROS2 Image message (BGR8 encoding)
        msg = self.bridge.cv2_to_imgmsg(image, encoding="bgr8")
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
