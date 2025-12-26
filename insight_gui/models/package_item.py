import gi

gi.require_version("GObject", "2.0")
from gi.repository import GObject, Gio


# TODO implement this
class PackageItem(GObject.GObject):
    __gtype_name__ = "PackageItem"

    path = GObject.Property()
