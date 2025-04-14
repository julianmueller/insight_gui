import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Gsk, Graphene, GObject


# from: https://gist.github.com/SpikedPaladin/29be3bfa8fba7e1d4701d0eec508c0ad
class Zoomable(GObject.GObject):
    __gype_name__ = "Zoomable"

    zoom_factor = GObject.Property(type=float, default=1.0)
    zoom_speed = GObject.Property(type=float, default=0.1)
    zoom_min = GObject.Property(type=float, default=0.1)
    zoom_max = GObject.Property(type=float, default=10.0)
    zoom_anchor_x = GObject.Property(type=float, default=0.0)
    zoom_anchor_y = GObject.Property(type=float, default=0.0)

    def __init__(self):
        super().__init__()
        self._zoom_children = set()
        self.connect("notify::zoom-factor", self.on_zoom_changed)

        self._scroll_controller = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        self._scroll_controller.connect("scroll", self.on_scroll)

        # We delay attaching the controller until the parent class is ready
        self._pending_attach_controller = True

    def add_zoom_child(self, widget):
        self._zoom_children.add(widget)

    def on_zoom_changed(self, *args):
        self.queue_allocate()

    def zoom_by(self, dy):
        step = dy * self.zoom_speed * self.zoom_factor
        self.set_zoom_factor(max(self.zoom_min, min(self.zoom_factor - step, self.zoom_max)))

    # Scroll handler (zoom with Ctrl + scroll)
    def on_scroll(self, controller, dx, dy):
        event = controller.get_current_event()
        if event and (event.get_modifier_state() & Gdk.ModifierType.CONTROL_MASK):
            # Get cursor position in widget coordinates
            # device = event.get_device()
            # pos = event.get_position()
            # print(pos)
            # self.zoom_anchor_x = pos.x
            # self.zoom_anchor_y = pos.y

            self.zoom_by(dy)
            return True
        return False

    def attach_zoom_controller(self):
        # Call this after the widget is fully initialized (e.g. in subclass __init__)
        self.add_controller(self._scroll_controller)
        self._pending_attach_controller = False

    # Allocation of children using transformed coordinates
    def do_size_allocate(self, width, height, baseline=0):
        GObject.GObject.do_size_allocate(self, width, height, baseline)

        for child in self._zoom_children:
            if not child.get_visible():
                continue
            _, nat = child.get_preferred_size()
            px = self.zoom_anchor_x
            py = self.zoom_anchor_y
            z = self.zoom_factor
            transform = (
                Gsk.Transform().translate(Graphene.Point(px, py)).scale(z, z).translate(Graphene.Point(-px, -py))
            )
            child.allocate(100, 100, nat.width, nat.height, baseline, transform)
