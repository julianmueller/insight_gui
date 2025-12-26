import gi

gi.require_version("GObject", "2.0")
from gi.repository import GObject

from insight_gui.models.interface_item import TopicInterfaceTypeItem


class TopicItem(GObject.GObject):
    __gtype_name__ = "TopicItem"

    name = GObject.Property(type=str, default="")
    namespace = GObject.Property(type=str, default="/")
    hidden = GObject.Property(type=bool, default=False)
    interface = GObject.Property(type=TopicInterfaceTypeItem)
    # i just ignore that there could be multiple types of interfaces, because i think that it is stupid

    subscriber_count = GObject.Property(type=int, default=0)
    publisher_count = GObject.Property(type=int, default=0)

    def __init__(self, *args, interface_full_name: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.interface = TopicInterfaceTypeItem(full_name=interface_full_name)

    @GObject.Property(type=str)
    def full_name(self) -> str:
        return f"{self.namespace if self.namespace != '/' else ''}/{self.name}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: '{self.full_name}'>"
