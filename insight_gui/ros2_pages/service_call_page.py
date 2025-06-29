# =============================================================================
# service_call_page.py
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

import yaml
import json
import threading

from rosidl_runtime_py import set_message_fields
from rosidl_runtime_py.utilities import get_service
from rosidl_runtime_py import message_to_yaml, message_to_csv, message_to_ordereddict

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, Pango, GObject

from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow, TextViewRow
from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage
from insight_gui.utils.gtk_utils import find_str_in_list_store


class ServiceCallPage(ContentPage):
    __gtype_name__ = "ServiceCallPage"

    def __init__(self, preselect_service: str = "", **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().set_title("Call a Service")
        super().set_refresh_fail_text("No services found. Refresh to try again.")

        self.preselect_service = preselect_service
        self.detach_kwargs = {"preselect_service": preselect_service}

        self.request_class = None
        self.request_instance = None
        self.response_class = None
        self.response_instance = None

        self.call_btn = super().add_bottom_left_btn(
            label="Call Service",
            icon_name="call-start-symbolic",
            func=self.on_call_service,
            tooltip_text="Call the selected service",
            css_classes=["suggested-action"],
        )
        self.clear_btn = super().add_bottom_right_btn(
            label="Clear", icon_name="trash-symbolic", func=self.on_clear_text, css_classes=["destructive-action"]
        )

        # select group
        self.select_group = self.pref_page.add_group(title="Select Service")
        self.service_row = self.select_group.add_row(
            Adw.ComboRow(
                title="Service",
                enable_search=True,
                use_subtitle=True,
                css_classes=["property"],
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.service_row.connect("notify::selected-item", self.on_service_selected)
        self.service_type_row = self.select_group.add_row(PrefRow(title="Service Type", css_classes=["property"]))

        # Create a Gio.ListStore to fill the ComboBox with
        self.service_list_store: Gio.ListStore = Gio.ListStore.new(Gtk.StringObject)
        self.service_row.set_model(self.service_list_store)

        def _on_factory_setup(factory, list_item):
            label = Gtk.Label(
                xalign=0,
                ellipsize=Pango.EllipsizeMode.MIDDLE,
                max_width_chars=50,
            )
            list_item.set_child(label)

        def _on_factory_bind(factory, list_item):
            item = list_item.get_item()
            label = list_item.get_child()
            if item and label:
                label.set_text(item.get_string())

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", _on_factory_setup)
        factory.connect("bind", _on_factory_bind)
        self.service_row.set_factory(factory)

        # TODO maybe merge the two rows, to match the visuals of the service info page

        self.msg_format_row = self.select_group.add_row(
            Adw.ComboRow(
                title="Message Format",
                use_subtitle=True,
                css_classes=["property"],
                # model=Gtk.StringList.new(["YAML", "Euler JSON"]),
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.msg_format_row.connect("notify::selected-item", self.on_msg_format_changed)
        self.msg_format_list_store = Gio.ListStore.new(Gtk.StringObject)
        self.msg_format_list_store.append(Gtk.StringObject.new("YAML"))
        # self.msg_format_list_store.append(Gtk.StringObject.new("CSV"))
        self.msg_format_list_store.append(Gtk.StringObject.new("JSON"))
        self.msg_format_row.set_model(self.msg_format_list_store)
        self.msg_format = "YAML"

        # request group
        self.request_group = self.pref_page.add_group(title="Request")
        self.request_group.add_suffix_btn(
            icon_name="edit-undo-symbolic", tooltip_text="Reset Request Content", func=self.update_request_text
        )
        self.request_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy Request Text",
            func=self.on_copy_request_to_clipboard,
        )
        self.request_text_view_row = self.request_group.add_row(TextViewRow(editable=True, wrap_mode=Gtk.WrapMode.NONE))

        # response group
        self.response_group = self.pref_page.add_group(title="Response")
        self.response_group.add_suffix_btn(
            icon_name="edit-copy-symbolic",
            tooltip_text="Copy Response Text",
            func=self.on_copy_response_to_clipboard,
        )
        # self.response_group.add_suffix_btn(
        #     icon_name="trash-symbolic", tooltip_text="Clear Response Text", func=self.on_clear_response, css_classes=["destructive-action"]
        # )
        self.response_text_view_row = self.response_group.add_row(
            TextViewRow(editable=False, wrap_mode=Gtk.WrapMode.NONE)
        )

    def refresh_bg(self) -> bool:
        self.available_services = self.ros2_connector.get_available_services()
        return len(self.available_services) > 0

    def refresh_ui(self):
        # fill the ComboBox/ListStore with available services
        for service_name, _service_types in self.available_services:
            self.service_list_store.append(Gtk.StringObject.new(service_name))

        # set the selected service to the preselected one
        found_index = find_str_in_list_store(self.service_list_store, self.preselect_service)
        # found, found_index = self.service_list_store.find(Gtk.StringObject.new(self.preselect_service))
        if found_index >= 0:
            self.service_row.set_selected(found_index)
        else:
            self.service_row.set_selected(0)

    def reset_ui(self):
        # clear previous service list
        self.service_list_store.remove_all()
        self.request_text_view_row.clear()
        self.response_text_view_row.clear()
        self.call_btn.set_sensitive(False)

    def trigger(self):
        self.call_service()

    def on_clear_text(self, *args):
        self.response_text_view_row.clear()
        self.response_instance = None

    def on_service_selected(self, *args):
        if self.service_list_store.get_n_items() <= 0:
            return

        self.selected_service_name = self.service_row.get_selected_item().get_string()
        self.service_class = self.ros2_connector.get_service_class(service_name=self.selected_service_name)
        self.selected_service_type = self.ros2_connector.get_service_type_name(self.service_class)
        self.service_type_row.set_subtitle(self.selected_service_type)
        self.service_type_row.set_subpage_link(
            nav_view=self.nav_view,
            subpage_class=InterfaceInfoPage,
            subpage_kwargs={"interface_full_name": self.selected_service_type},
        )

        self.request_class = self.service_class.Request
        self.request_instance = self.request_class()
        self.call_btn.set_sensitive(True)
        self.update_request_text()

    def on_msg_format_changed(self, *args):
        if not self.request_instance:
            return

        self.msg_format = self.msg_format_row.get_selected_item().get_string()
        self.update_request_text()
        self.update_response_text()

    def update_request_text(self):
        if not self.request_instance:
            return

        def _idle():
            self.request_text_view_row.set_text(request_text)

        self.request_instance = self.request_class()  # rese instance
        if self.msg_format == "YAML":
            request_text = message_to_yaml(self.request_instance).rstrip()
        elif self.msg_format == "JSON":
            request_text = str(json.dumps(message_to_ordereddict(self.request_instance), indent=4))

        GLib.idle_add(_idle)

    def update_response_text(self):
        if not self.response_instance:
            return

        def _idle():
            self.response_text_view_row.set_text(response_text)

        if self.msg_format == "YAML":
            response_text = message_to_yaml(self.response_instance).rstrip()
        elif self.msg_format == "JSON":
            response_text = str(json.dumps(message_to_ordereddict(self.response_instance), indent=4))

        GLib.idle_add(_idle)

    def on_call_service(self, *args):
        self.call_service()

    def call_service(self):
        request_text = self.request_text_view_row.get_text()

        if self.msg_format == "YAML":
            try:
                data_dict = yaml.safe_load(request_text)
            except Exception as e:
                super().show_toast(f"Invalid YAML: {e}")
                return

        elif self.msg_format == "JSON":
            try:
                data_dict = json.loads(request_text)
            except Exception as e:
                super().show_toast(f"Invalid JSON: {e}")
                return

        try:
            set_message_fields(
                msg=self.request_instance,
                values=data_dict,
            )
        except Exception as e:
            super().show_toast(f"Error parsing the request data: {e}")
            return

        def _thread_worker():
            self.call_btn.set_sensitive(False)
            try:
                self.response_instance = self.ros2_connector.call_service(
                    srv_type=self.service_class,
                    srv_name=self.selected_service_name,
                    request=self.request_instance,
                    timeout_sec=2,
                )
            except Exception as e:
                self.show_toast(f"Service Error: {e}")
                self.call_btn.set_sensitive(True)
                return

            def _update_text_field():
                if self.msg_format == "YAML":
                    response_text = message_to_yaml(self.response_instance)
                elif self.msg_format == "JSON":
                    response_text = str(json.dumps(message_to_ordereddict(self.response_instance), indent=4))

                self.response_text_view_row.set_text(response_text)
                self.call_btn.set_sensitive(True)

            GLib.idle_add(_update_text_field)

        threading.Thread(target=_thread_worker, daemon=True).start()

    def on_copy_request_to_clipboard(self, *args):
        clip = self.get_clipboard()
        text = self.request_text_view_row.get_text()
        clip.set(str(text))
        self.show_toast("Request text copied!")

    def on_copy_response_to_clipboard(self, *args):
        clip = self.get_clipboard()
        text = self.response_text_view_row.get_text()
        clip.set(str(text))
        self.show_toast("Response text copied!")
