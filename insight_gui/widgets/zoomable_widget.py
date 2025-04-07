import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Gsk, Graphene, GObject

# from: https://gist.github.com/SpikedPaladin/29be3bfa8fba7e1d4701d0eec508c0ad
class ZoomableWidget(Gtk.Widget, Gtk.Scrollable):
    __gype_name__ = "ZoomableWidget"

    hadjustment = GObject.Property(type=Gtk.Adjustment)
    vadjustment = GObject.Property(type=Gtk.Adjustment)
    hscroll_policy = GObject.Property(type=Gtk.ScrollablePolicy, default=Gtk.ScrollablePolicy.MINIMUM)
    vscroll_policy = GObject.Property(type=Gtk.ScrollablePolicy, default=Gtk.ScrollablePolicy.MINIMUM)
    zoom_factor = GObject.Property(type=float, default=1.0)
    zoom_speed = GObject.Property(type=float, default=0.1)

    def __init__(self):
        super().__init__()
        self.hadjustment = Gtk.Adjustment()
        self.vadjustment = Gtk.Adjustment()
        self.last_drag_point = Graphene.Point(0, 0)
        # self.zoom_factor = 1.0
        # self.zoom_speed = 0.05  # default, can be tuned
        self.custom_width = 1000.0
        self.custom_height = 1000.0
        self.last_drag_point = Graphene.Point(0, 0)

        self.set_overflow(Gtk.Overflow.HIDDEN)

        # Add a test child widget
        button = Gtk.Button(label="Test button")
        button.set_parent(self)

        # Scroll controller for zooming
        scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        scroll.connect("scroll", self.on_scroll)
        self.add_controller(scroll)

        self.connect("notify::zoom-factor", self.on_zoom_changed)

        # Drag controller for panning
        drag = Gtk.GestureDrag()
        drag.set_button(Gdk.BUTTON_MIDDLE)
        drag.connect("drag-begin", self.on_drag_begin)
        drag.connect("drag-update", self.on_drag_update)
        drag.connect("drag-end", self.on_drag_end)
        self.add_controller(drag)
        self.pan_offset = Graphene.Point(0.0, 0.0)

    # Properties required by Gtk.Scrollable
    def get_hadjustment(self):
        return self.hadjustment

    def set_hadjustment(self, adj):
        self.hadjustment = adj
        if adj:
            adj.connect("value-changed", lambda a: self.queue_allocate())

    def get_vadjustment(self):
        return self.vadjustment

    def set_vadjustment(self, adj):
        self.vadjustment = adj
        if adj:
            adj.connect("value-changed", lambda a: self.queue_allocate())

    def get_hscroll_policy(self):
        return self.hscroll_policy

    def get_vscroll_policy(self):
        return self.vscroll_policy

    def on_zoom_changed(self, *args):
        self.queue_allocate()

    # Scroll handler (zoom with Ctrl + scroll)
    def on_scroll(self, controller, dx, dy):
        event = controller.get_current_event()
        if event and (event.get_modifier_state() & Gdk.ModifierType.CONTROL_MASK):
            # self.zoom_factor = max(0.1, min(self.zoom_factor + self.zoom_speed * -dy, 10.0))
            direction = -dy
            scale_step = self.zoom_factor * self.zoom_speed
            new_zoom = self.zoom_factor + direction * scale_step
            self.zoom_factor = max(0.1, min(new_zoom, 20.0))
            print(self.zoom_factor)
            return True
        return False

    # Middle mouse drag handlers
    def on_drag_begin(self, gesture, start_x, start_y):
        print("drag begin", start_x, start_y)
        self.set_cursor(Gdk.Cursor.new_from_name("grabbing", None))
        self.last_drag_point = Graphene.Point(start_x, start_y)

    def on_drag_update(self, gesture, offset_x, offset_y):
        print("drag update", offset_x, offset_y)
        delta_x = self.last_drag_point.x - offset_x
        delta_y = self.last_drag_point.y - offset_y
        self.hadjustment.set_value(self.hadjustment.get_value() + delta_x)
        self.vadjustment.set_value(self.vadjustment.get_value() + delta_y)
        self.pan_offset = Graphene.Point(
            self.pan_offset.x + delta_x / self.zoom_factor, self.pan_offset.y + delta_y / self.zoom_factor
        )
        self.last_drag_point = Graphene.Point(offset_x, offset_y)

    def on_drag_end(self, gesture, offset_x, offset_y):
        print("drag end", offset_x, offset_y)
        self.set_cursor(None)

    # Transform used for zoom + scroll offset
    def screen_transform(self):
        transform = Gsk.Transform()
        transform = transform.translate(Graphene.Point(-self.hadjustment.get_value(), -self.vadjustment.get_value()))
        transform = transform.translate(Graphene.Point(self.pan_offset.x, self.pan_offset.y))
        transform = transform.scale(self.zoom_factor, self.zoom_factor)
        return transform
        # return (
        #     Gsk.Transform()
        #     .translate(Graphene.Point(-self.hadjustment.get_value(), -self.vadjustment.get_value()))
        #     .scale(self.zoom_factor, self.zoom_factor)
        # )

    # Allocation of children using transformed coordinates
    def do_size_allocate(self, width, height, baseline):
        x = self.hadjustment.get_value()
        y = self.vadjustment.get_value()

        child = self.get_first_child()
        while child:
            if not child.get_visible():
                child = child.get_next_sibling()
                continue

            min_size, nat_size = child.get_preferred_size()

            transform = self.screen_transform().translate(Graphene.Point(50, 50))
            child.allocate(nat_size.width, nat_size.height, baseline, transform)
            child = child.get_next_sibling()

        self.hadjustment.configure(
            x, 0, max(width, self.custom_width * self.zoom_factor), 0.1 * width, 0.9 * width, width
        )
        self.vadjustment.configure(
            y, 0, max(height, self.custom_height * self.zoom_factor), 0.1 * height, 0.9 * height, height
        )

    # Required for Gtk.Scrollable, but unused in this context
    def get_border(self):
        return False, Gtk.Border()
