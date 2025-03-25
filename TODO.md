# TODO List

## Marketing

- make a proper logo (help!)
- redo all screenshots before release

## Features

- global new features
    - find a way to load all "refresh" content on startup, also if one page updates "available_nodes" etc, all other pages that utilize this shall update as well
    - make shortcuts (eg CTRL+F) work and add shortcuts page (they should also work via actions and for detached windows)
    - add Gtk/Gio Notifications
    - add gtk settings
    - add gtk action for all major actions

- additional pages
    - add a teleop page
    - add tf inspection subpage (show the stuff that rviz shows)
    - add a controller "/joy" page (also look into Workbench - Gamepad Demo)
    - add a launch page to directly launch nodes with a set of arguments
    - (optional) add a URDF/robot_description viewer
    - (optional) add a rosbag page

- extend existing features
    - add an "echo" group for topics_info_page (and call for services etc), to listen to current data on the topic
        - maybe just add a row to a subpage to echo/call that topic/service
    - add constants to be visible in msg definitions (like ur_msgs/msg/SetIO)
    - add the ros wiki explainations for packages? like what are all possible subscribed/published topics? or just a btn?
    - extend preferences dialog
    - add option to add new env variables in the pref dialog (and add a refresh btn)
    - add a refresh to all "static" pages, e.g. TopicInfoPage, as this might also change while it is open
    - add when a new window is opened as a detach, make it have the same content as the detached content_page
    - add for all row descriptions etc a max line limit! (robot description param hold the whole urdf file, which results in a mile long description) so it is concat after some content length

- ros2 stuff
    - (optional) add every page of the gui as a ros2 executable, so a window with only this page starts

- stuff no working yet
    - make "set parameter" work
    - make btns of img viewer work
    - check continuous img stream
    - make btns in interface list filtering work

## Refactor

- remove "status_page" in window.ui
- rename all function, to fit GTK style "on_xxx" and "do_xxx"
- merge all "msg_type_info_page" etc into one class when differs in what it displays depending on the interface type
- clean up the mess of XXX.connect_(..., func(**func_kwargs)) and connect_data(...) and rather use connect(..., data)
- replace "webbrowser" stuff with gtk File/Web Launcher

## Bug Fixes

- banner reload throws an error!
- gui still sometimes freezes
- Search bar does not always have "focus" when a subpage is popped from the nav_view - then the row has focus?

