#!/usr/bin/env python

# standard imports
import os
import sys
import threading
import signal
import subprocess

# import queue
from pathlib import Path

# ros2 specific imports
import rclpy
from ament_index_python import get_package_share_directory

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio

# custom imports
from insight_gui.application import Ros2GuiApp


def main(args=None):
    # Set the global variable for all code to find the shared data directory
    share_dir = Path(get_package_share_directory("insight_gui")) / "data"

    # Enable Ctrl+C handling
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    try:
        gui_app = Ros2GuiApp(share_dir, start_ros2_connector=True)
        signal.signal(signal.SIGINT, lambda *_: gui_app.shutdown())
        gui_app.run(None)
    except Exception as e:
        gui_app.shutdown()


if __name__ == "__main__":
    main()
