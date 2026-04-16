import gi

gi.require_version("GObject", "2.0")
from gi.repository import GObject

from .node_item import NodeItem


# TODO implement full parameter functionality
class ParameterItem(GObject.GObject):
    __gtype_name__ = "ParameterItem"

    name = GObject.Property(type=str, default="")
    node = GObject.Property(type=NodeItem)
    description = GObject.Property(type=str, default="")
    type = GObject.Property(type=object, default=None)  # noqa: A003
    type_str = GObject.Property(type=str, default="")
    value = GObject.Property(type=object, default=None)
    read_only = GObject.Property(type=bool, default=False)
    dynamic_typing = GObject.Property(type=bool, default=False)

    integer_range = GObject.Property(type=object, default=None)
    floating_point_range = GObject.Property(type=object, default=None)
    additional_constraints = GObject.Property(type=object, default=None)

    # TODO add identification of "qos" param prefix?

    @GObject.Property(type=str)
    def full_name(self) -> str:
        return f"{self.node.full_name}:{self.name}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: '{self.full_name}'>"
