#!/usr/bin/env python

# =============================================================================
# main.py
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

import sys
import signal
import argparse

# from insight_gui.application import InsightApplication


def main(args=None):
    # Enable Ctrl+C handling
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--page",
        help="Start the application with the specified page open",
        type=str,
        metavar="PAGE_ID",
        default="",
    )
    parser.add_argument(
        "--list-pages",
        help="List all available pages",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--dummy-ros2",
        help="Use a dummy ROS2 connector that simulates ROS2 interactions without requiring a real ROS2 environment",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--debugpy",
        help="Enable debugpy and wait for debugger to attach on port 5678",
        default=False,
        action="store_true",
    )
    args = parser.parse_args(args)

    # Handle starting page argument
    start_page_id = None
    if args.page:
        from insight_gui.pages import all_pages, get_all_page_ids

        page_ids = get_all_page_ids()
        if args.page not in page_ids:
            print(f"Error: Page ID '{args.page}' not found. Use '--list-pages' to see all available pages.")
            sys.exit(1)

        start_page_id = args.page

    # list all available pages and exit
    if args.list_pages:
        from insight_gui.pages import all_pages, get_all_page_ids

        print("Available pages ('title' # ID):\n")
        for group in all_pages:
            print(f"{group.title}")
            for page in group.pages:
                print(f"\t'{page.title}' # {page.page_id}")
        sys.exit(0)

    # Handle dummy ROS2 connector argument
    dummy_ros2 = False
    if args.dummy_ros2:
        print("Using dummy ROS2 connector. No real ROS2 interactions will occur.")
        # The actual switching to the dummy connector is handled in the InsightApplication class
        dummy_ros2 = True

    # use debugpy for remote debugging if requested
    if args.debugpy:
        try:
            # Make sure to install debugpy with pip if not already installed
            import debugpy

            print("Starting debugpy... Waiting for debugger to attach.")
            debugpy.listen(("0.0.0.0", 5678))
            debugpy.wait_for_client()
        except ImportError:
            print("debugpy is not installed. Please install it with 'pip install debugpy'")

    # Start the application
    try:
        from insight_gui.application import InsightApplication

        gui_app = InsightApplication(start_page_id=start_page_id, dummy_ros2=dummy_ros2)
        signal.signal(signal.SIGINT, gui_app.shutdown)
        gui_app.run(None)

    except Exception as e:
        print(f"An error occurred: {e}")
        gui_app.shutdown()


if __name__ == "__main__":
    main()
