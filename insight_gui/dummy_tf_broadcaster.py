# =============================================================================
# dummy_tf_broadcaster.py
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

import math
import numpy as np
import random

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster
# import tf2_ros


class DummyTFBroadcaster(Node):
    def __init__(self):
        super().__init__("dummy_tf_broadcaster")

        # # Create a TransformBroadcaster
        # self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # # Timer to publish transforms at 10Hz
        # self.timer = self.create_timer(0.1, self.publish_transform)

        self.tf_static_broadcaster = StaticTransformBroadcaster(self)
        self.publish_transform()

        self.get_logger().info("Dummy TF Publisher is running...")

    def publish_transform(self):
        for tf_i in range(20):
            # Create a TransformStamped message
            t = TransformStamped()

            t.header.stamp = self.get_clock().now().to_msg()
            t.header.frame_id = random.choices(["world", *[f"child{tf}" for tf in range(tf_i)]])[0]
            t.child_frame_id = f"child{tf_i}"

            t.transform.translation.x = np.random.uniform(-1.0, 1.0)
            t.transform.translation.y = np.random.uniform(-1.0, 1.0)
            t.transform.translation.z = np.random.uniform(-1.0, 1.0)

            t.transform.rotation.x = np.random.uniform(-1.0, 1.0)
            t.transform.rotation.y = np.random.uniform(-1.0, 1.0)
            t.transform.rotation.z = np.random.uniform(-1.0, 1.0)
            t.transform.rotation.w = np.random.uniform(-1.0, 1.0)

            # Publish the transform
            # self.tf_broadcaster.sendTransform(t)
            self.tf_static_broadcaster.sendTransform(t)


def main():
    rclpy.init()
    node = DummyTFBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
