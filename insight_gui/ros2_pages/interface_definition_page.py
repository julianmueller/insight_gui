# =============================================================================
# interface_definition_page.py
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
from typing import Type

from rosidl_runtime_py import message_to_yaml, message_to_csv, message_to_ordereddict

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.pref_rows import TextViewRow
from insight_gui.widgets.buttons import CopyButton


class InterfaceDefinitionPage(ContentPage):
    __gtype_name__ = "InterfaceDefinitionPage"

    def __init__(self, interface_full_name: str, interface_class: Type, **kwargs):
        super().__init__(searchable=False, refreshable=False, **kwargs)
        super().set_title(f"Interface Definition {interface_full_name}")
        # TODO this needs to resemble whether its a Request/Response etc

        self.interface_full_name = interface_full_name
        self.intface_class = interface_class
        self.detach_kwargs = {
            "interface_full_name": interface_full_name,
            "interface_class": interface_class,
        }

        self.interface_instance = interface_class()

    def on_realize(self, *args):
        super().on_realize()

        # YAML Message Text
        yaml_text = message_to_yaml(self.interface_instance).rstrip()

        # TODO make it, that the scroll window shriks, when content is smaller than "max size"
        # TODO test it with "action_tutorials_interfaces/action/Fibonacci" that a min hight is show, even with no content
        yaml_group = self.pref_page.add_group(title="YAML")
        yaml_group.add_suffix_widget(
            CopyButton(
                copy_text=yaml_text,
                tooltip_text="Copy YAML",
                toast_host=self.toast_overlay,
                toast_text="YAML text copied!",
            ),
        )
        yaml_text_view = yaml_group.add_row(TextViewRow(editable=False))
        yaml_text_view.set_text(yaml_text)

        # JSON Message Text
        json_text = str(json.dumps(message_to_ordereddict(self.interface_instance), indent=4)).replace('"', "'")
        json_group = self.pref_page.add_group(title="JSON")
        json_group.add_suffix_widget(
            CopyButton(
                copy_text=json_text,
                tooltip_text="Copy JSON",
                toast_host=self.toast_overlay,
                toast_text="JSON text copied!",
            ),
        )
        json_text_view = json_group.add_row(TextViewRow(editable=False))
        json_text_view.set_text(json_text)

        # CSV Message Text
        csv_text = message_to_csv(self.interface_instance)
        csv_group = self.pref_page.add_group(title="CSV")
        csv_group.add_suffix_widget(
            CopyButton(
                copy_text=csv_text,
                tooltip_text="Copy CSV",
                toast_host=self.toast_overlay,
                toast_text="CSV text copied!",
            ),
        )
        csv_text_view = csv_group.add_row(TextViewRow(editable=False))
        csv_text_view.set_text(csv_text)
