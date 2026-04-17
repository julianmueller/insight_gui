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
        "--debugpy",
        help="Enable debugpy and wait for debugger to attach on port 5678",
        default=False,
        action="store_true",
    )
    args = parser.parse_args(args)

    # Handle starting page argument
    start_page_id = None
    if args.page:
        from insight_gui.pages import get_all_page_ids

        page_ids = get_all_page_ids()
        if args.page not in page_ids:
            sys.stderr.write(
                f"Error: Page ID '{args.page}' not found. Use '--list-pages' to see all available pages.\n"
            )
            sys.exit(1)

        start_page_id = args.page

    # list all available pages and exit
    if args.list_pages:
        from insight_gui.pages import all_pages

        lines = ["Available pages ('title' # ID):", ""]
        for group in all_pages:
            lines.append(f"{group.title}")
            for page in group.pages:
                lines.append(f"\t'{page.title}' # {page.page_id}")
        sys.stdout.write(f"{'\n'.join(lines)}\n")
        sys.exit(0)

    # use debugpy for remote debugging if requested
    if args.debugpy:
        try:
            # Make sure to install debugpy with pip if not already installed
            import debugpy

            sys.stderr.write("Starting debugpy... Waiting for debugger to attach.\n")
            debugpy.listen(("0.0.0.0", 5678))
            debugpy.wait_for_client()
        except ImportError:
            sys.stderr.write("debugpy is not installed. Please install it with 'pip install debugpy'\n")

    # Start the application
    gui_app = None
    try:
        from insight_gui.application import InsightApplication

        gui_app = InsightApplication(start_page_id=start_page_id)
        signal.signal(signal.SIGINT, gui_app.shutdown)
        gui_app.run(None)

    except Exception as e:
        sys.stderr.write(f"An error occurred: {e}\n")
        if gui_app:
            gui_app.shutdown()


if __name__ == "__main__":
    main()
