# Copyright (C) 2025  Julian Müller

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

#!/usr/bin/env python

# standard imports
import signal

# import queue
from pathlib import Path

# ros2 specific imports
import rclpy
from ament_index_python import get_package_share_directory


# custom imports
from insight_gui.application import Ros2GuiApp


def main(args=None):
    # Set the global variable for all code to find the shared data directory
    share_dir = Path(get_package_share_directory("insight_gui")) / "data"

    # Enable Ctrl+C handling
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # import debugpy
    # debugpy.listen(("0.0.0.0", 5678))
    # debugpy.wait_for_client()

    try:
        gui_app = Ros2GuiApp(share_dir)
        signal.signal(signal.SIGINT, lambda *_: gui_app.shutdown())
        gui_app.run(None)
    except Exception as e:
        gui_app.shutdown()


if __name__ == "__main__":
    main()
