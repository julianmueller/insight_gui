# =============================================================================
# msg_type_info_pages.py
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

import webbrowser
import json

from rosidl_runtime_py.utilities import get_message, get_service, get_action
from rosidl_runtime_py import message_to_yaml, message_to_csv, message_to_ordereddict
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
from gi.repository import Gtk, Adw

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.pref_group import PrefGroup
from insight_gui.widgets.pref_rows import PrefRow, TextViewRow


class MessageTypeInfoPage(ContentPage):
    __gtype_name__ = "MessageTypeInfoPage"

    def __init__(self, msg_type_full_name: str, **kwargs):
        super().__init__(searchable=False, refreshable=False, **kwargs)
        super().set_title(f"Message Type <{msg_type_full_name}>")
        super().set_search_entry_placeholder_text("Search for message types")

        self.msg_type_full_name = msg_type_full_name
        self.detach_kwargs = {"msg_type_full_name": msg_type_full_name}

    def on_realize(self, *args):
        super().on_realize(*args)

        # Load the message parent class
        msg_class = get_message(self.msg_type_full_name)

        # Btn for opening the online link to msg definition
        super().add_header_btn(
            icon_name="webpage-symbolic",
            tooltip_text="Online Definition",
            func=_on_open_msg_webpage,
            msg_type_full_name=self.msg_type_full_name,
        )

        # Constants Group
        constants_group = self.pref_page.add_group(title="Constants")
        constants_group.add_row(PrefRow(title="TODO implement this"))
        # TODO implement to show constants

        # Message Type
        msg_group = self.pref_page.add_group(title="Message")
        _populate_group_w_msg_rows(msg_class=msg_class, pref_group=msg_group, nav_view=self.nav_view)

        # Btn for opening the raw msg text dialog
        msg_group.add_suffix_btn(
            icon_name="notes-app-symbolic",
            tooltip_text="Raw Message Text",
            func=_on_open_msg_type_dialog,
            parent=self,
            msg_type_full_name=self.msg_type_full_name,
            msg_class=msg_class,
        )


class ServiceTypeInfoPage(ContentPage):
    __gtype_name__ = "ServiceTypeInfoPage"

    def __init__(self, srv_type_full_name: str, **kwargs):
        super().__init__(searchable=False, refreshable=False, **kwargs)
        super().set_title(f"Service Type <{srv_type_full_name}>")
        super().set_search_entry_placeholder_text("Search for service types")

        self.srv_type_full_name = srv_type_full_name
        self.detach_kwargs = {"srv_type_full_name": srv_type_full_name}

    def on_realize(self, *args):
        super().on_realize(*args)

        # Load the service parent class
        srv_class = get_service(self.srv_type_full_name)

        # Btn for opening the online link to msg definition
        super().add_header_btn(
            icon_name="webpage-symbolic",
            tooltip_text="Online Definition",
            func=_on_open_msg_webpage,
            msg_type_full_name=self.srv_type_full_name,
        )

        # Constants Group
        constants_group = self.pref_page.add_group(title="Constants")
        constants_group.add_row(PrefRow(title="TODO implement this"))
        # TODO implement to show constants

        # Service Message Request
        request_group = self.pref_page.add_group(title="Request", empty_group_text="No request data")
        request_class = srv_class.Request
        _populate_group_w_msg_rows(msg_class=request_class, pref_group=request_group, nav_view=self.nav_view)

        # Btn for opening the raw msg text dialog
        request_group.add_suffix_btn(
            icon_name="notes-app-symbolic",
            tooltip_text="Raw Message Text",
            visible=not request_group.is_empty,
            func=_on_open_msg_type_dialog,
            parent=self,
            msg_type_full_name=f"{self.srv_type_full_name} - Request",
            msg_class=request_class,
        )

        # Service Message Response
        response_group = self.pref_page.add_group(title="Response", empty_group_text="No response data")
        response_class = srv_class.Response
        _populate_group_w_msg_rows(msg_class=response_class, pref_group=response_group, nav_view=self.nav_view)

        # Btn for opening the raw msg text dialog
        response_group.add_suffix_btn(
            icon_name="notes-app-symbolic",
            tooltip_text="Raw Message Text",
            visible=not response_group.is_empty,
            func=_on_open_msg_type_dialog,
            parent=self,
            msg_type_full_name=f"{self.srv_type_full_name} - Response",
            msg_class=response_class,
        )

        # # Service Message Event
        # event_group = self.pref_page.add_group(title="Event")
        # event_class = srv_class.Event
        # _populate_group_w_msg_rows(msg_class=event_class, pref_group=event_group, nav_view=self.nav_view)

        # # Btn for opening the raw msg text dialog
        # event_group.add_suffix_btn(
        #     icon_name="notes-app-symbolic",
        #     tooltip_text="Raw Message Text",
        #     visible=not event_group.is_empty,
        #     func=_on_open_msg_type_dialog,
        #     parent=self,
        #     msg_type_full_name=f"{srv_type_full_name} - Event",
        #     msg_class=event_class,
        # )


class ActionTypeInfoPage(ContentPage):
    __gtype_name__ = "ActionTypeInfoPage"

    def __init__(self, act_type_full_name: str, **kwargs):
        super().__init__(searchable=False, refreshable=False, **kwargs)
        super().set_title(f"Action Type <{act_type_full_name}>")
        super().set_search_entry_placeholder_text("Search for action types")

        self.act_type_full_name = act_type_full_name
        self.detach_kwargs = {"act_type_full_name": act_type_full_name}

    def on_realize(self, *args):
        super().on_realize(*args)

        # Load the action parent class
        act_class = get_action(self.act_type_full_name)

        # Btn for opening the online link to msg definition
        super().add_header_btn(
            icon_name="webpage-symbolic",
            tooltip_text="Online Definition",
            func=_on_open_msg_webpage,
            msg_type_full_name=self.act_type_full_name,
        )

        # Constants Group
        constants_group = self.pref_page.add_group(title="Constants")
        constants_group.add_row(PrefRow(title="TODO implement this"))
        # TODO implement to show constants

        # Action Message Goal
        goal_group = self.pref_page.add_group(title="Goal", empty_group_text="No goal data")
        goal_class = act_class.Goal
        _populate_group_w_msg_rows(msg_class=goal_class, pref_group=goal_group, nav_view=self.nav_view)

        # Btn for opening the raw msg text dialog
        goal_group.add_suffix_btn(
            icon_name="notes-app-symbolic",
            tooltip_text="Raw Message Text",
            visible=not goal_group.is_empty,
            func=_on_open_msg_type_dialog,
            parent=self,
            msg_type_full_name=f"{self.act_type_full_name} - Goal",
            msg_class=goal_class,
        )

        # Action Message Feedback
        feedback_group = self.pref_page.add_group(title="Feedback", empty_group_text="No feedback data")
        feedback_class = act_class.Feedback
        _populate_group_w_msg_rows(msg_class=feedback_class, pref_group=feedback_group, nav_view=self.nav_view)

        # Btn for opening the raw msg text dialog
        feedback_group.add_suffix_btn(
            icon_name="notes-app-symbolic",
            tooltip_text="Raw Message Text",
            visible=not feedback_group.is_empty,
            func=_on_open_msg_type_dialog,
            parent=self,
            msg_type_full_name=f"{self.act_type_full_name} - Feedback",
            msg_class=feedback_class,
        )

        # Action Message Result
        result_group = self.pref_page.add_group(title="Result", empty_group_text="No result data")
        result_class = act_class.Result
        _populate_group_w_msg_rows(msg_class=result_class, pref_group=result_group, nav_view=self.nav_view)

        # Btn for opening the raw msg text dialog
        result_group.add_suffix_btn(
            icon_name="notes-app-symbolic",
            tooltip_text="Raw Message Text",
            visible=not result_group.is_empty,
            func=_on_open_msg_type_dialog,
            parent=self,
            msg_type_full_name=f"{self.act_type_full_name} - Result",
            msg_class=result_class,
        )

        # # Action Message Impl # TODO check what impl is
        # impl_group = self.pref_page.add_group(title="Impl")
        # impl_class = act_class.Impl
        # _populate_group_w_msg_rows(msg_class=impl_class, pref_group=impl_group, nav_view=self.nav_view)
        #
        # # Btn for opening the raw msg text dialog
        # result_group.add_suffix_btn(
        #     icon_name="notes-app-symbolic",
        #     tooltip_text="Raw Message Text",
        #     visible=not impl_group.is_empty,
        #     func=_on_open_msg_type_dialog,
        #     parent=self,
        #     msg_type_full_name=f"{act_type_full_name} - Impl",
        #     msg_class=impl_class,
        # )


def _on_open_msg_type_dialog(btn: Gtk.Button = None, *, parent: Gtk.Widget, msg_type_full_name: str, msg_class):
    dialog = MessageTypeDialog(msg_type_full_name=msg_type_full_name, msg_class=msg_class)
    dialog.present(parent=parent.get_root())


def _on_open_msg_webpage(btn: Gtk.Button = None, *, msg_type_full_name: str):
    # TODO jazzy uses this: https://docs.ros.org/en/ros2_packages/jazzy/api/example_interfaces/
    webbrowser.open(f"https://docs.ros2.org/foxy/api/{msg_type_full_name}.html")


# TODO this can be improved, especially the nested messages
def _populate_group_w_msg_rows(msg_class, pref_group: PrefGroup, nav_view: Adw.NavigationView):
    msg_instance = msg_class()
    # Iterate through the message fields
    for (field_name, field_type), slot_type in zip(
        msg_instance.get_fields_and_field_types().items(), msg_class.SLOT_TYPES
    ):
        field_value = getattr(msg_instance, field_name)
        # field_type='uint32'
        # type(field_value).__name__ = 'int'

        # for nested messages
        if isinstance(slot_type, NamespacedType):
            nested_msg_type_full_name = "/".join(slot_type.namespaced_name())
            row = PrefRow(title=field_name, subtitle=nested_msg_type_full_name)
            row.set_subpage_link(
                nav_view=nav_view,
                subpage_class=MessageTypeInfoPage,
                subpage_kwargs={"msg_type_full_name": nested_msg_type_full_name},
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
                    nav_view=nav_view,
                    subpage_class=MessageTypeInfoPage,
                    subpage_kwargs={"msg_type_full_name": nested_msg_type_full_name},
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


class MessageTypeDialog(Adw.PreferencesDialog):
    __gtype_name__ = "MessageTypeDialog"

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

        # JSON Message Text
        json_text = str(json.dumps(message_to_ordereddict(msg_instance))).replace('"', "'")
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

    def on_text_to_clipboard(self, text: str, text_type: str):
        clip = self.get_clipboard()
        clip.set(str(text))
        self.add_toast(Adw.Toast(title=f"{text_type} text copied!"))
