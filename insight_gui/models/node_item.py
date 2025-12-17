from __future__ import annotations
from typing import List, Tuple

import gi
from gi.repository import GObject, Gio


class NodeItem(GObject.GObject):
    __gtype_name__ = "NodeItem"

    namespace = GObject.Property(type=str, default="/")
    name = GObject.Property(type=str, default="")
    hidden = GObject.Property(type=bool, default=False)

    publisher_count = GObject.Property(type=int, default=0)
    subscriber_count = GObject.Property(type=int, default=0)
    service_server_count = GObject.Property(type=int, default=0)
    service_client_count = GObject.Property(type=int, default=0)
    action_server_count = GObject.Property(type=int, default=0)
    action_client_count = GObject.Property(type=int, default=0)

    parameters = GObject.Property(type=Gio.ListStore)

    @GObject.Property
    def full_name(self) -> str:
        return f"{self.namespace}{self.name}"

    @classmethod
    def from_tuple(cls, data: Tuple[str, str, str]) -> NodeItem:
        namespace, name, _ = data
        return cls(namespace=namespace, name=name)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} '{self.full_name}'>"
