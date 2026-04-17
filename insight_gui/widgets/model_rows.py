# =============================================================================
# model_rows.py
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

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GObject, Gtk, Adw, Gdk, GLib, Gio, Pango

from insight_gui.models.action_item import ActionItem
from insight_gui.models.interface_item import InterfaceTypeItem
from insight_gui.models.node_item import NodeItem
from insight_gui.models.package_item import PackageItem
from insight_gui.models.parameter_item import ParameterItem
from insight_gui.models.service_item import ServiceItem
from insight_gui.models.topic_item import TopicItem
from insight_gui.widgets.pref_rows import PrefRow


def _format_namespace(namespace: str | None) -> str:
    if namespace is None:
        return ""
    if namespace == "":
        return "/"
    return namespace


class ModelObjectRow(PrefRow):
    """Base row for rows backed by a GObject model item."""

    def __init__(
        self,
        *,
        model_item: GObject.GObject,
        drag_enabled: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model_item = model_item
        self._drag_source: Gtk.DragSource | None = None
        self._copy_action_separator_added = False

        if drag_enabled:
            self._add_model_drag_source()

    def _add_model_drag_source(self):
        self._drag_source = Gtk.DragSource()
        self._drag_source.set_actions(Gdk.DragAction.COPY)
        self._drag_source.connect("prepare", self._on_drag_prepare)
        self._drag_source.connect("drag-begin", self._on_drag_begin)
        self._drag_source.connect("drag-end", self._on_drag_end)
        self.add_controller(self._drag_source)

    def _on_drag_prepare(self, source: Gtk.DragSource, x: float, y: float):
        return Gdk.ContentProvider.new_for_value(self.model_item)

    def _on_drag_begin(self, source: Gtk.DragSource, drag: Gdk.Drag):
        self._primary_drag_cancelled = True
        drag_icon = Gtk.DragIcon.get_for_drag(drag)
        drag_icon.set_child(self._build_drag_icon())

    def _on_drag_end(self, source: Gtk.DragSource, drag: Gdk.Drag, delete_data: bool):
        if self._drag_finished_outside_window(drag):
            self._open_detached_info_page()

        self._primary_drag_cancelled = False

    def _drag_finished_outside_window(self, drag: Gdk.Drag) -> bool:
        if not self._get_info_page():
            return False
        if drag.get_selected_action():
            return False

        device = drag.get_device()
        source_surface = self._get_source_surface(drag)
        if not device or not source_surface:
            return False

        try:
            is_over_surface, x, y, _mask = source_surface.get_device_position(device)
        except (TypeError, RuntimeError):
            return False

        if not is_over_surface:
            return True

        return x < 0 or y < 0 or x >= source_surface.get_width() or y >= source_surface.get_height()

    def _get_source_surface(self, drag: Gdk.Drag) -> Gdk.Surface | None:
        native = self.get_native()
        if native:
            surface = native.get_surface()
            if surface:
                return surface

        return drag.get_surface()

    def _build_drag_icon(self) -> Gtk.Widget:
        width = max(240, min(self.get_allocated_width(), 360))
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            width_request=width,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
            css_classes=["card", "view"],
        )

        header = Gtk.Label(
            label=self.model_item.__item_type__,  # _drag_model_name(),
            xalign=0,
            ellipsize=Pango.EllipsizeMode.END,
            single_line_mode=True,
            max_width_chars=24,
            margin_top=8,
            margin_bottom=0,
            margin_start=10,
            margin_end=10,
            css_classes=["caption", "accent"],
        )
        box.append(header)

        title = Gtk.Label(
            label=self.get_title(),
            xalign=0,
            ellipsize=Pango.EllipsizeMode.END,
            single_line_mode=True,
            max_width_chars=48,
            margin_top=0,
            margin_bottom=0,
            margin_start=10,
            margin_end=10,
            css_classes=["heading"],
        )
        box.append(title)

        subtitle_text = self.get_subtitle()
        if subtitle_text:
            subtitle = Gtk.Label(
                label=subtitle_text,
                xalign=0,
                ellipsize=Pango.EllipsizeMode.MIDDLE,
                single_line_mode=True,
                max_width_chars=64,
                margin_top=0,
                margin_bottom=8,
                margin_start=10,
                margin_end=10,
                css_classes=["caption", "dim-label"],
            )
            box.append(subtitle)

        return box

    def _drag_model_name(self) -> str:
        if isinstance(self.model_item, NodeItem):
            return "Node"
        if isinstance(self.model_item, TopicItem):
            return "Topic"
        if isinstance(self.model_item, ServiceItem):
            return "Service"
        if isinstance(self.model_item, ActionItem):
            return "Action"
        if isinstance(self.model_item, PackageItem):
            return "Package"
        if isinstance(self.model_item, ParameterItem):
            return "Parameter"
        if isinstance(self.model_item, InterfaceTypeItem):
            return "Interface"

        return self.model_item.__class__.__name__.removesuffix("Item")

    def _get_info_page(self):
        return None

    def _open_detached_info_page(self) -> bool:
        info_page = self._get_info_page()
        if not info_page:
            return False

        app = Gio.Application.get_default()
        if not app:
            return False

        page_class, page_kwargs = info_page

        def _open_window():
            from insight_gui.window import DetachedWindow

            try:
                detached_window = DetachedWindow(
                    app=app,
                    nav_page_class=page_class,
                    nav_page_kwargs=page_kwargs,
                )
            except Exception as exc:
                connector = getattr(app, "ros2_connector", None)
                if connector:
                    connector.log(f"Failed to open detached detail window: {exc}", level="error")
                return GLib.SOURCE_REMOVE

            if hasattr(app, "detached_windows"):
                app.detached_windows.append(detached_window)
            detached_window.show()
            return GLib.SOURCE_REMOVE

        GLib.idle_add(_open_window, priority=GLib.PRIORITY_LOW)
        return True

    def _push_page(self, page_class, page_kwargs: dict):
        nav_view = self.get_ancestor(Adw.NavigationView)
        if nav_view:

            def _open_page():
                nav_view.push(page_class(**page_kwargs))
                return GLib.SOURCE_REMOVE

            GLib.idle_add(_open_page, priority=GLib.PRIORITY_LOW)

    def _set_copy_actions(self, entries: list[tuple[str, str, str]]):
        self.context_menu.clear()
        self._copy_action_separator_added = False
        for action_id, label, text in entries:
            fallback_label = label.removeprefix("Copy ").lower()
            self.context_menu.upsert_item(
                action_id,
                label,
                lambda text=text, fallback_label=fallback_label: self._copy_text_to_clipboard(
                    text,
                    fallback_label=fallback_label,
                ),
                icon_name="edit-copy-symbolic",
            )
        self._add_detached_info_action()

    def _add_detached_info_action(self):
        if not self._get_info_page():
            return

        self._add_model_action(
            "open-detached",
            f"Open {self._drag_model_name().lower()} detached",
            self._open_detached_info_page,
            icon_name="arrow2-top-right-symbolic",
        )

    def _add_model_action(self, action_id: str, label: str, callback: Callable, *, icon_name: str = ""):
        if self.context_menu.item_count > 0 and not self._copy_action_separator_added:
            self.context_menu.add_separator()
            self._copy_action_separator_added = True

        self.context_menu.upsert_item(action_id, label, callback, icon_name=icon_name)


class NodeRow(ModelObjectRow):
    __gtype_name__ = "NodeRow"

    node = GObject.Property(type=NodeItem)

    def __init__(self, *, node: NodeItem, nav_view: Adw.NavigationView | None = None, **kwargs):
        namespace = _format_namespace(node.namespace)
        super().__init__(model_item=node, title=node.name, subtitle=namespace, **kwargs)
        self.node = node

        if node.hidden:
            self.add_prefix_icon(icon_name="eye-not-looking-symbolic", tooltip_text="Hidden node")

        self.subtitle_lbl.set_tooltip_text(node.full_name)

        # improve filtering to include full name and namespace
        self.set_filter_str(f"{node.name} {namespace} {node.full_name}".lower())

        # node-specific context menu entries
        self._set_copy_actions(
            [
                ("copy-name", "Copy name", self.node.name),
                ("copy-namespace", "Copy namespace", namespace),
                ("copy-full-name", "Copy full name", self.node.full_name),
            ]
        )

        if nav_view:
            self.set_navigation_actions(nav_view)

    def set_navigation_actions(self, nav_view: Adw.NavigationView):
        page_class, page_kwargs = self._get_info_page()

        self.set_subpage_link(
            nav_view=nav_view,
            subpage_class=page_class,
            subpage_kwargs=page_kwargs,
            label="Show node info page",
        )

    def _get_info_page(self):
        from insight_gui.ros2_pages.node_info_page import NodeInfoPage

        return NodeInfoPage, {"node": self.node}


class TopicRow(ModelObjectRow):
    __gtype_name__ = "TopicRow"

    topic = GObject.Property(type=TopicItem)

    def __init__(self, *, topic: TopicItem, nav_view: Adw.NavigationView | None = None, **kwargs):
        super().__init__(model_item=topic, title=topic.full_name, subtitle=topic.interface.full_name, **kwargs)
        self.topic = topic

        if topic.hidden:
            self.add_prefix_icon(icon_name="eye-not-looking-symbolic", tooltip_text="Hidden topic")

        self.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.START)
        self.subtitle_lbl.set_tooltip_text(topic.full_name)

        self.set_filter_str(
            f"{topic.name} {_format_namespace(topic.namespace)} {topic.full_name} {topic.interface.full_name}".lower()
        )

        self._set_copy_actions(
            [
                ("copy-name", "Copy name", self.topic.name),
                ("copy-namespace", "Copy namespace", _format_namespace(self.topic.namespace)),
                ("copy-full-name", "Copy full name", self.topic.full_name),
                ("copy-interface", "Copy interface", self.topic.interface.full_name),
            ]
        )

        if nav_view:
            self.set_navigation_actions(nav_view)

    def set_navigation_actions(self, nav_view: Adw.NavigationView):
        from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage
        from insight_gui.ros2_pages.topic_pub_page import TopicPublisherPage
        from insight_gui.ros2_pages.topic_remap_page import TopicRemapPage
        from insight_gui.ros2_pages.topic_sub_page import TopicSubscriberPage
        page_class, page_kwargs = self._get_info_page()

        self.set_subpage_link(
            nav_view=nav_view,
            subpage_class=page_class,
            subpage_kwargs=page_kwargs,
            label="Show topic info page",
        )
        self._add_model_action(
            "publish-topic",
            "Publish to topic",
            lambda: self._push_page(TopicPublisherPage, {"preselect_topic": self.topic}),
            icon_name="rss-feed-symbolic",
        )
        self._add_model_action(
            "subscribe-topic",
            "Subscribe to topic",
            lambda: self._push_page(TopicSubscriberPage, {"preselect_topic": self.topic}),
            icon_name="subscriptions-symbolic",
        )
        self._add_model_action(
            "remap-topic",
            "Remap topic",
            lambda: self._push_page(TopicRemapPage, {"preselect_topic": self.topic}),
            icon_name="tactic-symbolic",
        )
        self._add_model_action(
            "open-interface",
            "Open interface",
            lambda: self._push_page(InterfaceInfoPage, {"interface": self.topic.interface}),
            icon_name="shapes-symbolic",
        )

    def _get_info_page(self):
        from insight_gui.ros2_pages.topic_info_page import TopicInfoPage

        return TopicInfoPage, {"topic": self.topic}


class ServiceRow(ModelObjectRow):
    __gtype_name__ = "ServiceRow"

    service = GObject.Property(type=ServiceItem)

    def __init__(self, *, service: ServiceItem, nav_view: Adw.NavigationView | None = None, **kwargs):
        super().__init__(model_item=service, title=service.full_name, subtitle=service.interface.full_name, **kwargs)
        self.service = service

        if service.hidden:
            self.add_prefix_icon(icon_name="eye-not-looking-symbolic", tooltip_text="Hidden service")

        self.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.START)
        self.subtitle_lbl.set_tooltip_text(service.full_name)

        self.set_filter_str(
            f"{service.name} {_format_namespace(service.namespace)} {service.full_name} {service.interface.full_name}".lower()
        )

        self._set_copy_actions(
            [
                ("copy-name", "Copy name", self.service.name),
                ("copy-namespace", "Copy namespace", _format_namespace(self.service.namespace)),
                ("copy-full-name", "Copy full name", self.service.full_name),
                ("copy-interface", "Copy interface", self.service.interface.full_name),
            ]
        )

        if nav_view:
            self.set_navigation_actions(nav_view)

    def set_navigation_actions(self, nav_view: Adw.NavigationView):
        from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage
        from insight_gui.ros2_pages.service_call_page import ServiceCallPage
        page_class, page_kwargs = self._get_info_page()

        self.set_subpage_link(
            nav_view=nav_view,
            subpage_class=page_class,
            subpage_kwargs=page_kwargs,
            label="Show service info page",
        )
        self._add_model_action(
            "call-service",
            "Call service",
            lambda: self._push_page(ServiceCallPage, {"preselect_service": self.service}),
            icon_name="call-start-symbolic",
        )
        self._add_model_action(
            "open-interface",
            "Open interface",
            lambda: self._push_page(InterfaceInfoPage, {"interface": self.service.interface}),
            icon_name="shapes-symbolic",
        )

    def _get_info_page(self):
        from insight_gui.ros2_pages.service_info_page import ServiceInfoPage

        return ServiceInfoPage, {"service": self.service}


class ActionRow(ModelObjectRow):
    __gtype_name__ = "ActionRow"

    action = GObject.Property(type=ActionItem)

    def __init__(self, *, action: ActionItem, nav_view: Adw.NavigationView | None = None, **kwargs):
        super().__init__(model_item=action, title=action.full_name, subtitle=action.interface.full_name, **kwargs)
        self.action = action

        if action.hidden:
            self.add_prefix_icon(icon_name="eye-not-looking-symbolic", tooltip_text="Hidden action")

        self.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.START)
        self.subtitle_lbl.set_tooltip_text(action.full_name)

        self.set_filter_str(
            f"{action.name} {_format_namespace(action.namespace)} {action.full_name} {action.interface.full_name}".lower()
        )

        self._set_copy_actions(
            [
                ("copy-name", "Copy name", self.action.name),
                ("copy-namespace", "Copy namespace", _format_namespace(self.action.namespace)),
                ("copy-full-name", "Copy full name", self.action.full_name),
                ("copy-interface", "Copy interface", self.action.interface.full_name),
            ]
        )

        if nav_view:
            self.set_navigation_actions(nav_view)

    def set_navigation_actions(self, nav_view: Adw.NavigationView):
        from insight_gui.ros2_pages.action_goal_page import ActionGoalPage
        from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage
        page_class, page_kwargs = self._get_info_page()

        self.set_subpage_link(
            nav_view=nav_view,
            subpage_class=page_class,
            subpage_kwargs=page_kwargs,
            label="Show action info page",
        )
        self._add_model_action(
            "send-goal",
            "Send goal",
            lambda: self._push_page(ActionGoalPage, {"preselect_action": self.action}),
            icon_name="emoji-flags-symbolic",
        )
        self._add_model_action(
            "open-interface",
            "Open interface",
            lambda: self._push_page(InterfaceInfoPage, {"interface": self.action.interface}),
            icon_name="shapes-symbolic",
        )

    def _get_info_page(self):
        from insight_gui.ros2_pages.action_info_page import ActionInfoPage

        return ActionInfoPage, {"action": self.action}


class PackageRow(ModelObjectRow):
    __gtype_name__ = "PackageRow"

    package = GObject.Property(type=PackageItem)

    def __init__(self, *, package: PackageItem, nav_view: Adw.NavigationView | None = None, **kwargs):
        super().__init__(model_item=package, title=package.name, subtitle=package.path, **kwargs)
        self.package = package
        self._set_copy_actions(
            [
                ("copy-name", "Copy name", self.package.name),
                ("copy-path", "Copy path", self.package.path),
            ]
        )
        self.set_filter_str(f"{package.name} {package.path}".lower())

        if nav_view:
            self.set_navigation_actions(nav_view)

    def set_navigation_actions(self, nav_view: Adw.NavigationView):
        page_class, page_kwargs = self._get_info_page()

        self.set_subpage_link(
            nav_view=nav_view,
            subpage_class=page_class,
            subpage_kwargs=page_kwargs,
            label="Show package info page",
        )

    def _get_info_page(self):
        from insight_gui.ros2_pages.pkg_info_page import PackageInfoPage

        return PackageInfoPage, {"pkg": self.package}


class ParameterRow(ModelObjectRow):
    __gtype_name__ = "ParameterRow"

    parameter = GObject.Property(type=ParameterItem)

    def __init__(self, *, parameter: ParameterItem, nav_view: Adw.NavigationView | None = None, **kwargs):
        subtitle = "Parameter type unavailable" if not parameter.type else f"{parameter.type_str}: {parameter.value}"
        super().__init__(model_item=parameter, title=parameter.name, subtitle=subtitle, **kwargs)
        self.parameter = parameter

        if parameter.read_only:
            self.add_prefix_icon(icon_name="lock-alt-symbolic", tooltip_text="Read-only parameter")

        self._set_copy_actions(
            [
                ("copy-name", "Copy name", self.parameter.name),
                ("copy-full-name", "Copy full name", self.parameter.full_name),
                ("copy-value", "Copy value", str(self.parameter.value)),
            ]
        )
        self.set_filter_str(f"{parameter.name} {parameter.full_name} {parameter.type_str} {parameter.value}".lower())

        if nav_view and parameter.type:
            self.set_navigation_actions(nav_view)

    def set_navigation_actions(self, nav_view: Adw.NavigationView):
        from insight_gui.ros2_pages.node_info_page import NodeInfoPage
        page_class, page_kwargs = self._get_info_page()

        self.set_subpage_link(
            nav_view=nav_view,
            subpage_class=page_class,
            subpage_kwargs=page_kwargs,
            label="Edit parameter",
        )
        self._add_model_action(
            "open-node",
            "Open node",
            lambda: self._push_page(NodeInfoPage, {"node": self.parameter.node}),
            icon_name="token-symbolic",
        )

    def _get_info_page(self):
        if not self.parameter.type:
            return None

        from insight_gui.ros2_pages.param_edit_page import ParamEditPage

        return ParamEditPage, {"parameter": self.parameter}


class InterfaceTypeRow(ModelObjectRow):
    __gtype_name__ = "InterfaceTypeRow"

    interface = GObject.Property(type=InterfaceTypeItem)

    def __init__(self, *, interface: InterfaceTypeItem, nav_view: Adw.NavigationView | None = None, **kwargs):
        super().__init__(
            model_item=interface,
            title=interface.name,
            subtitle=interface.full_name,
            tags=[interface.interface_class],
            **kwargs,
        )
        self.interface = interface
        self._set_copy_actions(
            [
                ("copy-name", "Copy name", self.interface.name),
                ("copy-package", "Copy package", self.interface.package),
                ("copy-full-name", "Copy full name", self.interface.full_name),
            ]
        )
        self.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.START)
        self.subtitle_lbl.set_tooltip_text(interface.full_name)
        self.set_filter_str(f"{interface.name} {interface.package} {interface.full_name}".lower())

        if nav_view:
            self.set_navigation_actions(nav_view)

    def set_navigation_actions(self, nav_view: Adw.NavigationView):
        page_class, page_kwargs = self._get_info_page()

        self.set_subpage_link(
            nav_view=nav_view,
            subpage_class=page_class,
            subpage_kwargs=page_kwargs,
            label="Open interface",
        )

    def _get_info_page(self):
        from insight_gui.ros2_pages.interface_info_page import InterfaceInfoPage

        return InterfaceInfoPage, {"interface": self.interface}
