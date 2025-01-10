import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


# same order as with css margins
# https://developer.mozilla.org/en-US/docs/Web/CSS/margin#syntax
def set_margin(widget: Gtk.Widget, margin: list | int):
    """
    Convenience function for setting the margins of a GTK.Widget as:
        - one value for all
        - 2x list: [top & bottom, right=end & left=start]
        - 3x list: [top, right=end & left=start, bottom]
        - 4x list: [top, right=end, bottom, left=start]
    """
    m = margins_dict(margin)
    for k, v in m.items():
        widget.set_property(k, v)


def margins_dict(margin: list | int):
    """
    Convenience function for putting the margins in a dict, to be used for Gtk.Widget as properties:
        - one value for all
        - 2x list: [top & bottom, right=end & left=start]
        - 3x list: [top, right=end & left=start, bottom]
        - 4x list: [top, right=end, bottom, left=start]
    """
    if isinstance(margin, list) and len(margin) == 2:
        margin_top = margin[0]
        margin_bottom = margin[0]
        margin_end = margin[1]
        margin_start = margin[1]
    elif isinstance(margin, list) and len(margin) == 3:
        margin_top = margin[0]
        margin_end = margin[1]
        margin_start = margin[1]
        margin_bottom = margin[2]
    elif isinstance(margin, list) and len(margin) == 4:
        margin_top = margin[0]
        margin_end = margin[1]
        margin_bottom = margin[2]
        margin_start = margin[3]
    elif isinstance(margin, int):
        margin_top = margin
        margin_end = margin
        margin_bottom = margin
        margin_start = margin
    else:
        raise ValueError("malformatted margins")

    return {
        "margin_top": margin_top,
        "margin_end": margin_end,
        "margin_bottom": margin_bottom,
        "margin_start": margin_start,
    }


def add_css_classes(widget: Gtk.Widget, classes: list):
    """Convenience function for adding multiple css classes to a widget."""
    if not isinstance(widget, list):
        raise ValueError("malformatted css classes")

    for _class in classes:
        widget.add_css_class(_class)


def get_child_by_name(parent_widget, name):
    """Convenience function to get the child of a widget by its name."""
    first_child = parent_widget.get_first_child()
    last_child = parent_widget.get_last_child()

    # Iterate through siblings until the name matches or no more children exist
    child = first_child
    while child:
        if child.get_name() == name:
            return child
        # If we reach the last child and it's not the target, break out
        if child == last_child:
            break
        child = child.get_next_sibling()

    return None


def get_children(widget) -> list:
    first_child = widget.get_first_child()
    last_child = widget.get_last_child()
    children = []

    # Iterate through siblings until the name matches or no more children exist
    child = first_child
    while child:
        children.append(child)
        # If we reach the last child and it's not the target, break out
        if child == last_child:
            break
        child = child.get_next_sibling()

    return children
