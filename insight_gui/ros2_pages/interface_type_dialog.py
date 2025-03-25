# =============================================================================
# interface_type_dialog.py
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

import json

from rosidl_runtime_py import message_to_yaml, message_to_csv, message_to_ordereddict

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.pref_rows import TextViewRow


class InterfaceTypeDialog(Adw.PreferencesDialog):
    __gtype_name__ = "InterfaceTypeDialog"

    def __init__(self, msg_type_full_name: str, msg_class, **kwargs):
        super().__init__(**kwargs)
        super().set_title(str(msg_type_full_name))
        super().set_size_request(width=300, height=500)

        pref_page = PrefPage()
        super().add(pref_page)

        msg_instance = msg_class()

        # YAML Message Text
        yaml_text = message_to_yaml(msg_instance).rstrip()

        # TODO make it, that the scroll window shriks, when content is smaller than "max size"
        # TODO test it with "action_tutorials_interfaces/action/Fibonacci" that a min hight is show, even with no content
        yaml_group = pref_page.add_group(title="YAML")
        yaml_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy YAML",
            func=self.on_text_to_clipboard,
            text=yaml_text,
            text_type="YAML",
        )
        yaml_text_view = yaml_group.add_row(TextViewRow(editable=False))
        yaml_text_view.set_text(yaml_text)

        # JSON Message Text
        json_text = str(json.dumps(message_to_ordereddict(msg_instance), indent=4)).replace('"', "'")
        json_group = pref_page.add_group(title="JSON")
        json_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy JSON",
            func=self.on_text_to_clipboard,
            text=json_text,
            text_type="JSON",
        )
        json_text_view = json_group.add_row(TextViewRow(editable=False))
        json_text_view.set_text(json_text)

        # CSV Message Text
        csv_text = message_to_csv(msg_instance)
        csv_group = pref_page.add_group(title="CSV")
        csv_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy CSV",
            func=self.on_text_to_clipboard,
            text=csv_text,
            text_type="CSV",
        )
        csv_text_view = csv_group.add_row(TextViewRow(editable=False))
        csv_text_view.set_text(csv_text)

    def on_text_to_clipboard(self, text: str, text_type: str):
        clip = self.get_clipboard()
        clip.set(str(text))
        self.add_toast(Adw.Toast(title=f"{text_type} text copied!"))
