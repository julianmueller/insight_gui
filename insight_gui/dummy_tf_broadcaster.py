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

import rclpy
from rclpy.node import Node
import tf2_ros
from geometry_msgs.msg import TransformStamped


class DummyTFBroadcaster(Node):
    def __init__(self):
        super().__init__("dummy_tf_broadcaster")

        # Create a TransformBroadcaster
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # Timer to publish transforms at 10Hz
        self.timer = self.create_timer(0.1, self.publish_transform)

        self.get_logger().info("Dummy TF Publisher is running...")

    def publish_transform(self):
        # Create a TransformStamped message
        t1 = TransformStamped()
        t2 = TransformStamped()

        t1.header.stamp = self.get_clock().now().to_msg()
        t1.header.frame_id = "world"  # Parent frame
        t1.child_frame_id = "dummy_link1"  # Child frame

        t2.header.stamp = t1.header.stamp
        t2.header.frame_id = t1.child_frame_id
        t2.child_frame_id = "dummy_link2"  # Child frame

        # Set translation (x, y, z)
        t1.transform.translation.x = 1.0
        t1.transform.translation.y = 0.5
        t1.transform.translation.z = 0.0

        # Set rotation (as a quaternion)
        angle = self.get_clock().now().nanoseconds * 1e-9  # Rotate over time
        qx = 0.0
        qy = 0.0
        qz = math.sin(angle / 2.0)
        qw = math.cos(angle / 2.0)

        t1.transform.rotation.x = qx
        t1.transform.rotation.y = qy
        t1.transform.rotation.z = qz
        t1.transform.rotation.w = qw

        t2.transform = t1.transform

        # Publish the transform
        self.tf_broadcaster.sendTransform(t1)
        self.tf_broadcaster.sendTransform(t2)


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
