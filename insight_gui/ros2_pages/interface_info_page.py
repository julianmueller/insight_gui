# =============================================================================
# interface_info_pages.py
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

from __future__ import annotations
import os
import re
from typing import Type
from enum import Enum, auto

from rosidl_adapter.parser import PRIMITIVE_TYPES  # TODO use these and all the other definitions from this import
from rosidl_runtime_py import get_interface_path
from rosidl_runtime_py.utilities import get_message, get_service, get_action
from rosidl_parser.definition import (
    NamespacedType,
    UnboundedSequence,
    BoundedSequence,
    Array,
    BoundedString,
    UnboundedString,
    BoundedWString,
    UnboundedWString,
    BasicType,
)


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk

from insight_gui.ros2_pages.interface_definition_page import InterfaceDefinitionPage
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow


class InterfaceType(Enum):
    MSG = auto()
    SRV = auto()
    ACT = auto()

    @classmethod
    def infer_from_name(self, full_name: str) -> InterfaceType:
        if re.search(r"/msg/", full_name):
            return InterfaceType.MSG
        elif re.search(r"/srv/", full_name):
            return InterfaceType.SRV
        elif re.search(r"/action/", full_name):
            return InterfaceType.ACT


class InterfaceInfoPage(ContentPage):
    __gtype_name__ = "InterfaceInfoPage"

    def __init__(self, interface_full_name: str, interface_type: InterfaceType = None, **kwargs):
        super().__init__(searchable=True, refreshable=False, **kwargs)

        if interface_type is None:
            interface_type = InterfaceType.infer_from_name(interface_full_name)

        if interface_type == InterfaceType.MSG:
            super().set_title(f"Message Type {interface_full_name}")
            super().set_search_entry_placeholder_text("Search for message types")

        elif interface_type == InterfaceType.SRV:
            super().set_title(f"Service Type {interface_full_name}")
            super().set_search_entry_placeholder_text("Search for service types")

        elif interface_type == InterfaceType.ACT:
            super().set_title(f"Action Type {interface_full_name}")
            super().set_search_entry_placeholder_text("Search for action types")

        self.interface_full_name = interface_full_name
        self.interface_type = interface_type
        self.detach_kwargs = {"interface_full_name": interface_full_name, "interface_type": interface_type}

        # Btn for opening the definition file
        self.open_file_btn = super().add_bottom_left_btn(
            label="Open Definition File",
            icon_name="folder-documents-symbolic",
            tooltip_text="Open file that defines the interface",
            func=self.on_open_interface_file,
        )

        # Btn for opening the online link to msg definition
        self.open_link_btn = super().add_bottom_right_btn(
            label="Online Definition",
            icon_name="web-browser-symbolic",
            tooltip_text="Open definition online",
            func=self.on_open_weblink,
        )

    def refresh_bg(self):
        return True

    def refresh_ui(self):
        interface_classes = {}

        # Message
        if self.interface_type == InterfaceType.MSG:
            msg_class = get_message(self.interface_full_name)
            interface_classes["Message"] = msg_class
            constants = self.get_constants(msg_class)

        # Service
        elif self.interface_type == InterfaceType.SRV:
            srv_class = get_service(self.interface_full_name)
            interface_classes["Request"] = srv_class.Request
            interface_classes["Response"] = srv_class.Response
            constants = self.get_constants(srv_class.Request) | self.get_constants(srv_class.Response)

        # Action
        elif self.interface_type == InterfaceType.ACT:
            act_class = get_action(self.interface_full_name)
            interface_classes["Goal"] = act_class.Goal
            interface_classes["Feedback"] = act_class.Feedback
            interface_classes["Result"] = act_class.Result
            constants = (
                self.get_constants(act_class.Goal)
                | self.get_constants(act_class.Feedback)
                | self.get_constants(act_class.Result)
            )

        # Constants Group
        if len(constants) > 0:
            constants_group = self.pref_page.add_group(title="Constants")
            for const_name, const_value in constants.items():
                row: PrefRow = constants_group.add_row(PrefRow(title=const_name))
                row.add_suffix_lbl(label=const_value)

        for class_type, interface_class in interface_classes.items():
            group = self.pref_page.add_group(title=class_type, empty_group_text=f"Empty {class_type}")
            self.populate_group_w_msg_rows(interface_class=interface_class, pref_group=group)

            # Btn for opening the raw msg text dialog
            subpage_btn = group.add_suffix_widget(
                Gtk.Button(
                    icon_name="go-next-symbolic",
                    tooltip_text=f"Open {class_type} Definition",
                )
            )

            def _on_pressed(controller: Gtk.GestureClick, n_press: int, x: float, y: float):
                state = controller.get_current_event_state()
                subpage = InterfaceDefinitionPage(
                    interface_full_name=self.interface_full_name, interface_class=interface_class
                )

                # add CTRL+click functionality to open in detached window
                if state & Gdk.ModifierType.CONTROL_MASK:
                    subpage.detach()

                # regular click
                else:
                    self.nav_view.push(subpage)

            if hasattr(subpage_btn, "subpage_signal_handler"):
                subpage_btn.disconnect(self.subpage_signal_handler)

            gesture_click = Gtk.GestureClick(
                propagation_phase=Gtk.PropagationPhase.CAPTURE, propagation_limit=Gtk.PropagationLimit.NONE
            )
            self.subpage_signal_handler = gesture_click.connect("pressed", _on_pressed)
            subpage_btn.add_controller(gesture_click)

    def on_open_interface_file(self, *args):
        interface_file_path = get_interface_path(self.interface_full_name)
        if os.path.exists(interface_file_path):
            file = Gio.File.new_for_path(interface_file_path)
            Gtk.FileLauncher(file=file, always_ask=True, writable=False).launch(self.app.main_window, None)
        else:
            super().show_toast(f"Path '{interface_file_path}' does not exist!")

    def on_open_weblink(self, *args):
        Gio.AppInfo.launch_default_for_uri(f"https://docs.ros.org/en/jazzy/p/{self.interface_full_name}.html", None)

    def get_constants(self, interface_class: Type) -> dict:
        interface_instance = interface_class()
        constants = {}

        for field_name in dir(interface_instance):
            if field_name == "SLOT_TYPES":
                continue

            if re.match(r"^([A-Z]+(?:_|[A-Z]|[0-9])*)+", field_name):
                constants[field_name] = getattr(interface_instance, field_name)

        return constants

    # TODO this can be improved, especially the nested messages
    # maybe use rosidl_runtime_py.convert.get_message_slot_types
    def populate_group_w_msg_rows(self, interface_class: Type, pref_group: PrefGroup):
        interface_instance = interface_class()

        # Iterate through the message fields
        for (field_name, field_type), slot_type in zip(
            interface_instance.get_fields_and_field_types().items(), interface_class.SLOT_TYPES
        ):
            field_value = getattr(interface_instance, field_name)
            # field_type  = 'uint32'
            # field_value = e.g '42'
            # type(field_value).__name__ = 'int'

            # for nested messages
            if isinstance(slot_type, NamespacedType):
                nested_msg_type_full_name = "/".join(slot_type.namespaced_name())
                row = PrefRow(title=field_name, subtitle=nested_msg_type_full_name)
                row.set_subpage_link(
                    nav_view=self.nav_view,
                    subpage_class=InterfaceInfoPage,
                    subpage_kwargs={"interface_full_name": nested_msg_type_full_name},
                )

            # for numpy arrays
            # TODO this is still untested, as i cannot refind a msg type with a numpy array, but i swear ive seen one
            # elif isinstance(slot_type, np.ndarray):
            #     row = Adw.ExpanderRow(title=field_name, subtitle=field_type)
            #     row.add(PrefRow(title="Shape", suffix_lbl=field_value.shape))
            #     row.add(PrefRow(title="Dimensions", suffix_lbl=field_value.ndim))
            #     row.add(PrefRow(title="Data Type", suffix_lbl=field_value.dtype))
            #     row.add(PrefRow(title="Size", suffix_lbl=field_value.size))
            #     row.add(PrefRow(title="Value", suffix_lbl=field_value))

            # for sequences of defined lengths
            elif isinstance(slot_type, (UnboundedSequence, BoundedSequence)):
                if not isinstance(
                    slot_type.value_type, (BasicType, BoundedString, UnboundedString, BoundedWString, UnboundedWString)
                ):
                    nested_msg_type_full_name = "/".join(slot_type.value_type.namespaced_name())
                    row = PrefRow(title=field_name, subtitle=f"sequence of <{nested_msg_type_full_name}>")
                    row.set_subpage_link(
                        nav_view=self.nav_view,
                        subpage_class=InterfaceInfoPage,
                        subpage_kwargs={"interface_full_name": nested_msg_type_full_name},
                    )
                else:
                    if isinstance(slot_type.value_type, BasicType):
                        subtitle = f"sequence of <{slot_type.value_type.typename}>"
                    else:
                        subtitle = "sequence of <string>"

                    row = PrefRow(title=field_name, subtitle=subtitle)
                    row.add_prefix_icon("sudoku-app-symbolic")
                    row.add_suffix_lbl("<i>empty list</i>", use_markup=True)
                # field_value = field_value if field_value else "<i>empty list</i>"

            # for arrays
            elif isinstance(slot_type, Array):
                # Remove brackets and split the list
                content = str(field_value).strip("[]").split()
                total_count = len(content)

                if len(field_value) <= 6:
                    field_value = str(field_value)
                else:
                    field_value = f"[{content[0]} {content[1]} ... {content[-2]} {content[-1]}] <i>x{total_count}</i>"

                row = PrefRow(title=field_name, subtitle=field_type)
                row.add_prefix_icon("sudoku-app-symbolic")
                row.add_suffix_lbl(field_value, use_markup=True)

            # for strings
            elif isinstance(slot_type, (BoundedString, UnboundedString, BoundedWString, UnboundedWString)):
                row = PrefRow(title=field_name, subtitle=field_type)
                row.add_prefix_icon("sudoku-app-symbolic")
                row.add_suffix_lbl("<i>empty list</i>", use_markup=True)

            # for basic types
            elif isinstance(slot_type, BasicType):
                row = PrefRow(title=field_name, subtitle=field_type)
                row.add_prefix_icon("sudoku-app-symbolic")
                row.add_suffix_lbl(field_value)

            # add row to group
            pref_group.add_row(row)
