import gi

gi.require_version("GObject", "2.0")
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

    @GObject.Property(type=str)
    def full_name(self) -> str:
        return f"{self.namespace if self.namespace != '/' else ''}/{self.name}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: '{self.full_name}'>"
