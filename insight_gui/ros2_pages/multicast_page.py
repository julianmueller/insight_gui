# =============================================================================
# multicast_page.py
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

import threading
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Pango

from ros2multicast.api import send, receive

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow

DEFAULT_GROUP = "225.0.0.1"
DEFAULT_PORT = 49150


class MulticastPage(ContentPage):
    __gtype_name__ = "MulticastPage"

    def __init__(self, **kwargs):
        super().__init__(searchable=False, refreshable=False, **kwargs)
        super().set_title("Multicast Test")

        # self.pref_page.set_description("") # TODO add here some notes regarding the ros_domain_id etc setting

        # Threading
        self.receiver_thread = None

        # send group
        self.send_group = self.pref_page.add_group(title="Send", filterable=False)
        self.send_msg_row = self.send_group.add_row(
            Adw.EntryRow(title="Message Data", text="Hello World!", show_apply_button=True)
        )
        self.send_group_row = self.send_group.add_row(
            Adw.EntryRow(title="Group", text=DEFAULT_GROUP, show_apply_button=True)
        )
        self.send_port_row = self.send_group.add_row(
            Adw.EntryRow(title="Port", text=DEFAULT_PORT, show_apply_button=True)
        )
        self.send_ttl_row = self.send_group.add_row(Adw.EntryRow(title="TTL", text="", show_apply_button=True))

        # send button
        self.send_button = self.send_group.add_row(
            Gtk.Button(
                child=Adw.ButtonContent(
                    label="Send",
                    icon_name="rss-feed-symbolic",
                ),
                tooltip_text="Send Multicast Message",
                margin_top=12,
                halign=Gtk.Align.CENTER,
                css_classes=["suggested-action", "pill"],
            )
        )
        self.send_button.connect("clicked", self.on_send_clicked)

        # receive group
        self.receive_group = self.pref_page.add_group(title="Receive", filterable=False)
        self.receive_group_row = self.receive_group.add_row(Adw.EntryRow(title="Group", text=DEFAULT_GROUP))
        self.receive_port_row = self.receive_group.add_row(Adw.EntryRow(title="Port", text=DEFAULT_PORT))
        self.receive_timeout_row = self.receive_group.add_row(
            Adw.SpinRow(
                title="Timeout",
                subtitle="in seconds",
                digits=2,
                numeric=True,
                adjustment=Gtk.Adjustment(lower=0.1, upper=100.0, value=5.0, step_increment=1.0, page_increment=10),
            )
        )
        self.receive_msg_row = self.receive_group.add_row(
            PrefRow(title="Received Message Data", subtitle="", css_classes=["property"])
        )
        self.receive_msg_row.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.NONE)
        self.receive_msg_row.subtitle_lbl.set_single_line_mode(True)

        # send button
        self.receive_button = self.receive_group.add_row(
            Gtk.Button(
                child=Adw.ButtonContent(
                    label="Start Receiving",
                    icon_name="subscriptions-symbolic",
                ),
                tooltip_text="Receive Multicast Message",
                margin_top=12,
                halign=Gtk.Align.CENTER,
                css_classes=["suggested-action", "pill"],
            )
        )
        self.receive_button.connect("clicked", self.on_receive_clicked)

    def on_send_clicked(self, *args):
        # Get configuration
        try:
            msg = bytes(self.send_msg_row.get_text() or "Hello World!", "utf-8")
            group = self.send_group_row.get_text() or DEFAULT_GROUP
            port = int(self.send_port_row.get_text() or DEFAULT_PORT)
            ttl = self.send_ttl_row.get_text()

            if not ttl:
                ttl = None
            else:
                ttl = int(ttl)

            # Use ros2multicast.api.send
            send(msg, group=group, port=port, ttl=ttl)
        except Exception as e:
            self.show_toast(f"Error: {e}")
        finally:
            # Update send button row subtitle
            time_fmt = self._current_time_to_datetime().strftime("%Y-%m-%d %H:%M:%S.%f")
            self.send_group.set_description(f"Last sent at {time_fmt}")
            # self.show_toast("Multicast message sent")

    def on_receive_clicked(self, *args):
        # Get configuration values

        try:
            group = self.receive_group_row.get_text() or DEFAULT_GROUP
            port = int(self.receive_port_row.get_text() or DEFAULT_PORT)
            timeout = float(self.receive_timeout_row.get_value())
        except Exception as e:
            self.show_toast(f"Error: {e}")
            return

        def receiver_worker():
            # Worker thread to receive multicast messages.
            try:
                GLib.idle_add(self.receive_button.set_sensitive, False)
                message, (_host, _port) = receive(group=group, port=port, timeout=timeout)
                if message:
                    time_fmt = self._current_time_to_datetime().strftime("%Y-%m-%d %H:%M:%S.%f")
                    GLib.idle_add(
                        self.receive_msg_row.set_subtitle,
                        f"Received message from {_host}:{_port} at {time_fmt}: {message.decode('utf-8')}",
                    )
            except Exception as e:
                GLib.idle_add(self.receive_msg_row.set_subtitle, f"Error: {e}")
            finally:
                GLib.idle_add(self.receive_button.set_sensitive, True)

        if self.receiver_thread and self.receiver_thread.is_alive():
            self.receiver_thread.join()

        # Start receiver thread
        self.receiver_thread = threading.Thread(target=receiver_worker, daemon=True)
        self.receiver_thread.start()

    def _current_time_to_datetime(self) -> datetime:
        time_s, time_ns = self.ros2_connector.node.get_clock().now().seconds_nanoseconds()
        return datetime.fromtimestamp(float(time_s + time_ns / 1e9))
