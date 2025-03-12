import yaml

from ros2service.api import get_service_names_and_types, get_service_class
from rosidl_runtime_py import set_message_fields
from rosidl_runtime_py.utilities import get_service
from rosidl_runtime_py import message_to_yaml

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from insight_gui.ros2_connector import ROS2Connector
from insight_gui.widgets.content_page import ContentPage
from insight_gui.widgets.pref_page import PrefPage
from insight_gui.widgets.pref_rows import PrefRow, ButtonRow, SearchRow, TextViewRow

# from insight_gui.widgets.entry_row import EntryRow

from insight_gui.ros2_pages.msg_type_info_pages import ServiceTypeInfoPage


class ServiceCallPage(ContentPage):
    __gtype_name__ = "ServiceCallPage"

    def __init__(self, nav_view: Adw.NavigationView = None, ros2_connector: ROS2Connector = None, **kwargs):
        super().__init__(searchable=False, **kwargs)
        super().set_title("Service Call")

        self.nav_view = nav_view if nav_view else self.get_parent()
        self.ros2_connector = ros2_connector if ros2_connector else self.get_root().ros2_connector

        super().set_dedock_page(type(self), dedock_kwargs={"ros2_connector": self.ros2_connector})

        # select group
        self.select_group = self.pref_page.add_group(title="Select Service")

        self.service_select_row = self.select_group.add_row(
            Adw.ComboRow(
                title="Service",
                enable_search=True,
                expression=Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"),
            )
        )
        self.service_select_row.connect("notify::selected-item", self.on_service_selected)
        self.selected_service_type_row = self.select_group.add_row(
            PrefRow(title="Service Type", css_classes=["property"])
        )

        # Create a Gio.ListStore
        self.service_list_store: Gio.ListStore = Gio.ListStore.new(Gtk.StringObject)
        self.service_select_row.set_model(self.service_list_store)

        # TODO maybe merge the two rows, to match the visuals of the service info page
        # TODO make that:
        # - the request and response groups have a btn in the header, that opens the type dialog for request/response

        # request group
        self.request_group = self.pref_page.add_group(title="Request")
        self.request_group.add_suffix_btn(
            icon_name="edit-undo-symbolic", tooltip_text="Reset Request Text", func=self.on_service_selected
        )
        self.request_text_row = self.request_group.add_row(TextViewRow(editable=True))

        self.call_btn = self.request_group.add_row(
            ButtonRow(
                label="Call Service",
                start_icon_name="call-start-symbolic",
                func=lambda *_: GLib.idle_add(self.on_call_service),
                sensitive=False,
            )
        )

        # response group
        self.response_group = self.pref_page.add_group(title="Response")
        self.response_group.add_suffix_btn(
            icon_name="trash-symbolic", tooltip_text="Clear Response Text", func=self.on_clear_response
        )
        self.response_text_row = self.response_group.add_row(TextViewRow(editable=False))

    def refresh(self, *args):
        if not self.ros2_connector.is_running:
            # TODO now, the msg "refresh yielded no result" shows up, make it, that refresh is restarted
            super().show_toast_w_btn("ROS2 node not running", "Start Node", func=self.ros2_connector.start_node)
            return

        # clear previous service list
        self.service_list_store.remove_all()

        available_services = sorted(
            get_service_names_and_types(node=self.ros2_connector.node, include_hidden_services=True)
        )

        # Check if there are services to call
        if len(available_services) > 0:
            self.call_btn.set_sensitive(True)
        else:
            super().show_toast("No services found")
            self.call_btn.set_sensitive(False)
            return

        def on_setup(factory, list_item):
            label = Gtk.Label(xalign=0, wrap=True, hexpand=True)
            list_item.set_child(label)

        def on_bind(factory, list_item):
            item = list_item.get_item()
            label = list_item.get_child()
            if item and label:
                label.set_text(item.get_string())

        # TODO maybe also group the services by namespaces
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", on_setup)
        factory.connect("bind", on_bind)

        # fill the ComboBox/ListStore with available services
        for service_name, service_types in available_services:
            self.service_list_store.append(Gtk.StringObject.new(service_name))

        # self.service_select_row.set_model(list_store)
        self.service_select_row.set_factory(factory)
        # self.service_select_row.set_selected(0)

    def on_service_selected(self, *args):
        if self.service_list_store.get_n_items() <= 0:
            return

        self.selected_service_name = self.service_select_row.get_selected_item().get_string()
        self.service_class = get_service_class(
            node=self.ros2_connector.node,
            service_name=self.selected_service_name,
            include_hidden_services=True,
        )
        self.selected_service_type = get_msg_full_name(self.service_class)
        self.selected_service_type_row.set_subtitle(self.selected_service_type)
        self.selected_service_type_row.set_subpage_link(
            nav_view=self.nav_view,
            subpage_class=ServiceTypeInfoPage,
            srv_type_full_name=self.selected_service_type,
        )

        self.request_class = self.service_class.Request
        self.request_instance = self.request_class()
        yaml_text = message_to_yaml(self.request_instance).rstrip()
        self.request_text_row.set_text(yaml_text)

        # response_class = srv_class.Response
        # msg_instance = response_class()

    def on_call_service(self, *args):
        if not self.ros2_connector.is_running:
            super().show_toast_w_btn("ROS2 node not running", "Start Node", func=self.ros2_connector.start_node)
            return False

        request_yaml = self.request_text_row.get_text()
        try:
            data_dict = yaml.safe_load(request_yaml)
        except Exception as e:
            super().show_toast("Invalid YAML")
            return False

        try:
            set_message_fields(
                msg=self.request_instance,
                values=data_dict,
            )
        except Exception as e:
            super().show_toast("Error parsing the request data")
            return False

        response = self.ros2_connector.call_service(
            srv_name=self.selected_service_name,
            srv_type=self.service_class,
            request=self.request_instance,
        )

        response_yaml = message_to_yaml(response).rstrip()
        self.response_text_row.set_text(response_yaml)

        super().show_toast("Service call was successful")

        return False  # stop the Glib.idle_add

    def on_clear_response(self, *args):
        self.response_text_row.clear()


def get_msg_full_name(msg_class):
    module_name = msg_class.__module__
    package_name = module_name.split(".")[0]
    message_type = module_name.split(".")[1]
    message_name = msg_class.__name__
    return f"{package_name}/{message_type}/{message_name}"
