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

from insight_gui.application import InsightApplication


def main(args=None):
    # Enable Ctrl+C handling
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Make sure to install debugpy with pip if not already installed
    if "--debugpy" in sys.argv[1:]:
        import debugpy

        print("Starting debugpy... Waiting for debugger to attach.")
        debugpy.listen(("0.0.0.0", 5678))
        debugpy.wait_for_client()
        sys.argv.remove("--debugpy")

    try:
        gui_app = InsightApplication()
        signal.signal(signal.SIGINT, gui_app.shutdown)
        gui_app.run(None)

    except Exception as e:
        print(f"An error occurred: {e}")
        gui_app.shutdown()


if __name__ == "__main__":
    main()
