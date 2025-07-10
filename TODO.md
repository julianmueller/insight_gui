# TODO List

## Marketing

- make a proper logo (help!)
- redo all screenshots before release

## Features

- global new features:
    - ~~find a way to load all "refresh" content on startup~~
    - ~~also if one page updates "available_nodes" etc, all other pages that utilize this shall update as well~~
    - ~~make shortcuts (eg CTRL+F) work and add shortcuts page (they should also work via actions and for detached windows)~~
    - ~~add gtk settings~~
    - ~~add an argument to all pages (where applicable) to show specific content (like topic listener etc)~~
    - ~~add "spacebar" shortcut and action for "main page trigger", like "call page" or "start echo"~~
    - ~~add btn to "close all detatched windows", maybe in menu?~~
    - ~~CTRL+Click on navigation to open in detatched window instead of switching to that page~~
    - ~~CTRL+Click for every link/subpage to open in detatched window instead of switching to that page~~
    - ~~add when a new window is opened as a detach, make it have the same content as the detached content_page~~ (solved by caching)
    - add Gtk/Gio Notifications
    - add gtk action for all major actions
    - add "experimental" flag/info to not really working pages
    - Add a Link to the latest online tutorial, that explains eg how to subscribe etc
    - add context menu on right click, eg for all rows to copy, title or subtitle content, or open new window etc

- additional pages:
    - ~~add a `rqt_graph` equivalent page~~
    - ~~add a teleop page~~
    - ~~add a controller "/joy" page~~ (also look into Workbench - Gamepad Demo)
    - ~~add action send_goal~~
    - ~~add topic publisher (+once)~~
    - ~~add a refresh to all "static" pages, e.g. TopicInfoPage, as this might also change while it is open~~
    - ~~a launch page to directly launch nodes with a set of arguments~~
    - ~~add an overview page, where all pages are shown as cards (and are maybe grouped? and ofc searchable)~~
    - ~~static~~/dynamic tf2 broadcaster
    - tf inspection subpage (show the stuff that rviz shows)
    - service echo (listener)
    - qos info page
    - URDF/robot_description viewer
    - rosbag page
    - visualize/load/save octomaps
    - ros2control controller show/toggle page
    - monitor param changes
    - remap page, where topics and be remapped to another name?
    - documentation Page, with Links to the ros2 webpages? maybe even a webview renderer?
    - clock page with manipulation options
    - bookmarks page to save links to pages for later
        - use `book-ribbon-symbolic` and `bookmark-add-symbolic`
    - image pub page (load image/video and stream it)
        - use `linked-camera-symbolic` and 
        - also move the image pages then to its own group

- additional settings:
    - ~~maybe add an option, that all parameter-related services are hidden (/describe_parameters etc)~~
    - ~~add options to tune the caching (caching timeout, clear cache, etc)~~
    - ~~add opton to show/hide the breadcrumbs bar~~
    - add option to preferences to hide everything related to insight, like node, parameters etc
    - add option to add new env variables in the pref dialog (and add a refresh btn)
    - light/dark/system color theme

- page enhancements:
    - add a save btn to the interface page and topic echo and service call page
    - for topic pub/sub, service call, action goal pages, add a link to the interface definition page in the header of the textfields
    - Interface Info Page:
        - ~~add constants to be visible in msg definitions (like ur_msgs/msg/SetIO)~~
    - Package Info Page:
        - add the ros wiki explainations for packages? like what are all possible subscribed/published topics? or just a btn?
    - Param Page:
        - dump + load + save params
    - Topic Pub Page:
        - add hz etc sliders
    - Topic Sub Page:
        - add hz etc infos
    - Topic List Page:
        - "Open Echoer" is the wrong name for Subscribing
        - "Add Publisher" and "Add Subscriber" btns to the groups maybe instead?
    - Topic Info Page:
        - add hz, bw, qos etc. infos
        - add an "echo" group for topics_info_page (and call for services etc), to listen to current data on the topic
        - maybe just add a row to a subpage to echo/call that topic/service
    - Node Info Page:
        - start nodes with certain cli/ros2 arguments
    - Logger page:
        - save the list of log files as eg csv
        - inspect certain logs closer by double clicking them
    - graph page:
        - add a setting, that opens flap to the right
        - add services/actions/parameters
        - allow to toggle all these blocks
        - add blacklists
        - for topics/services/actions show the type as a subtitle?
        - instead of opening the blocks as their (node/topic/etc) page, a graph_local_page is opened, which shows only this block with its connections

- ros2 stuff
    - (optional) add every page of the gui as a ros2 executable, so a window with only this page starts

- stuff no working yet
    - ~~make "set parameter" work~~
    - ~~check continuous img stream~~
    - ~~resizing of the window also resizes the preference pages, or maybe even hides the sidebar (but it shall show no warnings!)~~
    - ~~make btns in interface list filtering work~~
    - add for all row descriptions etc a max line limit! (robot description param hold the whole urdf file, which results in a mile long description) so it is concat after some content length
    - make btns of img viewer work
    - some rows shall vexpand (like the logs) which is currently not working
    - with the caching in place, sometimes old topics/services are beeing displayed, and can be inspected in subpages. Add a warning/banner, when a info-subpage is opened for a non-existing topic/etc. that says that it is not beeing published anymore

## Refactor

- ~~merge all "msg_type_info_page" etc into one class when differs in what it displays depending on the interface type~~
- ~~replace "webbrowser" stuff with gtk File/Web Launcher~~
- ~~change that the overwritten _deferred_init of the subclasses of contentpage use the refresh methods instead~~
- ~~turn interface dialog into content page~~
- remove "status_page" in window.ui
- rename all function, to fit GTK style "on_xxx" and "do_xxx"
- clean up the mess of XXX.connect_(..., func(**func_kwargs)) and connect_data(...) and rather use connect(..., data)
- look into `from rclpy.expand_topic_name import expand_topic_name`
- change the whole connect to signals of rows, so that the signals of specific widgets are re-emitted by the row (like with the ScaleRow)
- replace all ros2cli commands with rclpy/rosidl etc commands
- be strict/consistent about private ("_") instance variables and method names!
- move expensive imports into methods/classes only where needed
- use CustomFilter in filter_func to ignore emptry_row etc
- change all "prints" into ros2_connector.logs
- add groups for common ros2 interfaces formats (Pose/Quaternion/Transform etc) where exisiting rows that are implemented (like tf calc page normalize quat etc) can be reused
    - maybe even for images??


## Bugs

- ~~fix ros2 clock (broken since actions update)~~
- ~~when the sidebar is collapsed and a different stack page is chosen, the "realize" function gets called again for the content pages and they dupe their rows etc~~
- ~~gui freezes when calling a not available (anymore) service~~
- ~~icons, that were added as gresource are not available in white when dark style is activated~~
- ~~gui still sometimes freezes~~
- banner reload throws an error!
- Search bar does not always have "focus" when a subpage is popped from the nav_view - then the row has focus?
- ellippsize throws sometimes an error if the label text is too short
- fix, that the link to the online-lookup of msg definitions is currently completely wrong (must point to the pkg the msgs is defined in)
- "Failed to realize renderer of type 'GskGLRenderer' for surface 'GdkX11Popup': GL-Kontext kann nicht erstellt werden"
- "Failed to realize renderer of type 'GskNglRenderer' for surface 'GdkX11Toplevel': GL-Kontext kann nicht erstellt werden"
- in pub:
    - when an exisiting topic is selected, then the topic name changed, the type changed and the name back to the suggested, an exisiting topic name will get a different type, which results in an error (RCLError)
- in topics with multiple message type, only one row is shown with the msg type (separated by comma), which leads to a nonexisting interface_info page, make this into multiple rows
