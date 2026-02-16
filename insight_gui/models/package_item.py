import gi

gi.require_version("GObject", "2.0")
from gi.repository import GObject


class PackageItem(GObject.GObject):
    __gtype_name__ = "PackageItem"

    name = GObject.Property(type=str, default="")
    path = GObject.Property(type=str, default="")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: '{self.name}'>"
