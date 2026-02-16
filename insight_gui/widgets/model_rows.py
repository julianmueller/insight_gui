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

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GObject, Pango

from insight_gui.models.action_item import ActionItem
from insight_gui.models.node_item import NodeItem
from insight_gui.models.service_item import ServiceItem
from insight_gui.models.topic_item import TopicItem
from insight_gui.widgets.pref_rows import PrefRow


def _format_namespace(namespace: str | None) -> str:
    if namespace is None:
        return ""
    if namespace == "":
        return "/"
    return namespace


class NodeRow(PrefRow):
    __gtype_name__ = "NodeRow"

    node = GObject.Property(type=NodeItem)

    def __init__(self, *, node: NodeItem, **kwargs):
        namespace = _format_namespace(node.namespace)
        super().__init__(title=node.name, subtitle=namespace, **kwargs)
        self.node = node

        if node.hidden:
            self.add_prefix_icon(icon_name="eye-not-looking-symbolic", tooltip_text="Hidden node")

        self.subtitle_lbl.set_tooltip_text(node.full_name)

        # improve filtering to include full name and namespace
        self.set_filter_str(f"{node.name} {namespace} {node.full_name}".lower())

        # node-specific context menu entries
        self.context_menu.clear()
        self.context_menu.upsert_item(
            "copy-name",
            "Copy name",
            lambda: self._copy_text_to_clipboard(self.node.name, fallback_label="name"),
        )
        self.context_menu.upsert_item(
            "copy-namespace",
            "Copy namespace",
            lambda: self._copy_text_to_clipboard(namespace, fallback_label="namespace"),
        )
        self.context_menu.upsert_item(
            "copy-full-name",
            "Copy full name",
            lambda: self._copy_text_to_clipboard(self.node.full_name, fallback_label="full name"),
        )


class TopicRow(PrefRow):
    __gtype_name__ = "TopicRow"

    topic = GObject.Property(type=TopicItem)

    def __init__(self, *, topic: TopicItem, **kwargs):
        super().__init__(title=topic.full_name, subtitle=topic.interface.full_name, **kwargs)
        self.topic = topic

        if topic.hidden:
            self.add_prefix_icon(icon_name="eye-not-looking-symbolic", tooltip_text="Hidden topic")

        self.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.START)
        self.subtitle_lbl.set_tooltip_text(topic.full_name)

        self.set_filter_str(
            f"{topic.name} {_format_namespace(topic.namespace)} {topic.full_name} {topic.interface.full_name}".lower()
        )

        self.context_menu.clear()
        self.context_menu.upsert_item(
            "copy-name",
            "Copy name",
            lambda: self._copy_text_to_clipboard(self.topic.name, fallback_label="name"),
        )
        self.context_menu.upsert_item(
            "copy-namespace",
            "Copy namespace",
            lambda: self._copy_text_to_clipboard(_format_namespace(self.topic.namespace), fallback_label="namespace"),
        )
        self.context_menu.upsert_item(
            "copy-full-name",
            "Copy full name",
            lambda: self._copy_text_to_clipboard(self.topic.full_name, fallback_label="full name"),
        )
        self.context_menu.upsert_item(
            "copy-interface",
            "Copy interface",
            lambda: self._copy_text_to_clipboard(self.topic.interface.full_name, fallback_label="interface"),
        )


class ServiceRow(PrefRow):
    __gtype_name__ = "ServiceRow"

    service = GObject.Property(type=ServiceItem)

    def __init__(self, *, service: ServiceItem, **kwargs):
        super().__init__(title=service.full_name, subtitle=service.interface.full_name, **kwargs)
        self.service = service

        if service.hidden:
            self.add_prefix_icon(icon_name="eye-not-looking-symbolic", tooltip_text="Hidden service")

        self.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.START)
        self.subtitle_lbl.set_tooltip_text(service.full_name)

        self.set_filter_str(
            f"{service.name} {_format_namespace(service.namespace)} {service.full_name} {service.interface.full_name}".lower()
        )

        self.context_menu.clear()
        self.context_menu.upsert_item(
            "copy-name",
            "Copy name",
            lambda: self._copy_text_to_clipboard(self.service.name, fallback_label="name"),
        )
        self.context_menu.upsert_item(
            "copy-namespace",
            "Copy namespace",
            lambda: self._copy_text_to_clipboard(_format_namespace(self.service.namespace), fallback_label="namespace"),
        )
        self.context_menu.upsert_item(
            "copy-full-name",
            "Copy full name",
            lambda: self._copy_text_to_clipboard(self.service.full_name, fallback_label="full name"),
        )
        self.context_menu.upsert_item(
            "copy-interface",
            "Copy interface",
            lambda: self._copy_text_to_clipboard(self.service.interface.full_name, fallback_label="interface"),
        )


class ActionRow(PrefRow):
    __gtype_name__ = "ActionRow"

    action = GObject.Property(type=ActionItem)

    def __init__(self, *, action: ActionItem, **kwargs):
        super().__init__(title=action.full_name, subtitle=action.interface.full_name, **kwargs)
        self.action = action

        if action.hidden:
            self.add_prefix_icon(icon_name="eye-not-looking-symbolic", tooltip_text="Hidden action")

        self.subtitle_lbl.set_ellipsize(Pango.EllipsizeMode.START)
        self.subtitle_lbl.set_tooltip_text(action.full_name)

        self.set_filter_str(
            f"{action.name} {_format_namespace(action.namespace)} {action.full_name} {action.interface.full_name}".lower()
        )

        self.context_menu.clear()
        self.context_menu.upsert_item(
            "copy-name",
            "Copy name",
            lambda: self._copy_text_to_clipboard(self.action.name, fallback_label="name"),
        )
        self.context_menu.upsert_item(
            "copy-namespace",
            "Copy namespace",
            lambda: self._copy_text_to_clipboard(_format_namespace(self.action.namespace), fallback_label="namespace"),
        )
        self.context_menu.upsert_item(
            "copy-full-name",
            "Copy full name",
            lambda: self._copy_text_to_clipboard(self.action.full_name, fallback_label="full name"),
        )
        self.context_menu.upsert_item(
            "copy-interface",
            "Copy interface",
            lambda: self._copy_text_to_clipboard(self.action.interface.full_name, fallback_label="interface"),
        )
