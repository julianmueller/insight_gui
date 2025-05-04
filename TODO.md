# TODO List

## Marketing

- make a proper logo (help!)
- redo all screenshots before release

## Features

- global new features
    - ~~find a way to load all "refresh" content on startup~~
    - also if one page updates "available_nodes" etc, all other pages that utilize this shall update as well
    - ~~make shortcuts (eg CTRL+F) work and add shortcuts page (they should also work via actions and for detached windows)~~
    - add Gtk/Gio Notifications
    - add gtk settings
    - add gtk action for all major actions
    - ~~add an argument to all pages (where applicable) to show specific content (like topic listener etc)~~
    - ~~add "spacebar" shortcut and action for "main page trigger", like "call page" or "start echo"~~
    - CTRL+Click on subpage to open in detatched window instead of pushing it to the open nav_view
    - ~~add btn to "close all detatched windows", maybe in menu?~~
    - add "experimental" flag/info to not really working pages like img stream
    - add option to preferences to hide everything related to insight, like node, parameters etc
    - add "monitor param changes"

- additional pages
    - ~~add a `rqt_graph` equivalent page~~
    - ~~add a teleop page~~
    - add a save btn to the interface dialog and topic echo and service call page
    - add static/dynamic tf2 broadcaster
    - add tf inspection subpage (show the stuff that rviz shows)
    - add a controller "/joy" page (also look into Workbench - Gamepad Demo)
    - add a launch page to directly launch nodes with a set of arguments
    - add action send_goal
    - add topic publisher (+once)
    - add service echo
    - (optional) add qos info page
    - (optional) add a URDF/robot_description viewer
    - (optional) add a rosbag page
    - (optional) add a page to visualize/load/save octomaps

- extend existing features
    - add an "echo" group for topics_info_page (and call for services etc), to listen to current data on the topic
        - maybe just add a row to a subpage to echo/call that topic/service
    - ~~add constants to be visible in msg definitions (like ur_msgs/msg/SetIO)~~
    - add the ros wiki explainations for packages? like what are all possible subscribed/published topics? or just a btn?
    - extend preferences dialog
    - add option to add new env variables in the pref dialog (and add a refresh btn)
    - ~~add a refresh to all "static" pages, e.g. TopicInfoPage, as this might also change while it is open~~
    - add when a new window is opened as a detach, make it have the same content as the detached content_page
    - topic info: add hz & bw
    - add ros2 param dump + load

- ros2 stuff
    - (optional) add every page of the gui as a ros2 executable, so a window with only this page starts

- stuff no working yet
    - add for all row descriptions etc a max line limit! (robot description param hold the whole urdf file, which results in a mile long description) so it is concat after some content length
    - make "set parameter" work
    - make btns of img viewer work
    - ~~check continuous img stream~~
    - make btns in interface list filtering work
    - ~~resizing of the window also resizes the preference pages, or maybe even hides the sidebar (but it shall show no warnings!)~~
    - some rows shall vexpand (like the logs) which is currently not working

## Refactor

- remove "status_page" in window.ui
- rename all function, to fit GTK style "on_xxx" and "do_xxx"
- ~~merge all "msg_type_info_page" etc into one class when differs in what it displays depending on the interface type~~
- clean up the mess of XXX.connect_(..., func(**func_kwargs)) and connect_data(...) and rather use connect(..., data)
- ~~replace "webbrowser" stuff with gtk File/Web Launcher~~
- look into `from rclpy.expand_topic_name import expand_topic_name`

## Bug Fixes

- banner reload throws an error!
- gui still sometimes freezes
- Search bar does not always have "focus" when a subpage is popped from the nav_view - then the row has focus?
- ~~fix ros2 clock (broken since actions update)~~
- ~~when the sidebar is collapsed and a different stack page is chosen, the "realize" function gets called again for the content pages and they dupe their rows etc~~
- icons, that were added as gresource are not available in white when dark style is activated (see https://developer.gnome.org/documentation/tutorials/themed-icons.html#symbolic-icons)
- gui freezes when calling a non available service
- ellippsize throws sometimes an error if the label text is too short
- change that the overwritten _deferred_init of the subclasses of contentpage use the refresh methods instead
- fix, that the link to the online-lookup of msg definitions is currently completely wrong (must point to the pkg the msgs is defined in)

## Snippets

- add CTRL+Click extra to a btn

```python
def on_button_pressed(self, gesture, n_press, x, y):
    state = gesture.get_current_event().get_state()
    if state & Gdk.ModifierType.CONTROL_MASK:
        print("Ctrl was held during click!")
        self.do_ctrl_click()
    else:
        print("Regular click")
        self.do_normal_click()

gesture = Gtk.GestureClick.new()
gesture.connect("pressed", self.on_button_pressed)
button.add_controller(gesture)
```