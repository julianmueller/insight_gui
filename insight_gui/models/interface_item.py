import re

import gi

gi.require_version("GObject", "2.0")
from gi.repository import GObject, Gio


def _log(message: str, level: str = "info") -> None:
    app = Gio.Application.get_default()
    connector = getattr(app, "ros2_connector", None)
    if connector:
        connector.log(message, level=level)


# see https://docs.ros.org/en/jazzy/Concepts/Basic/About-Interfaces.html
class FieldItem(GObject.GObject):
    __gtype_name__ = "FieldItem"

    """
    Each field consists of a type and a name, separated by a space, i.e:

    ```
    fieldtype1 fieldname1
    fieldtype2 fieldname2 fielddefaultvalue
    constanttype CONSTANTNAME=constantvalue
    ```

    For example:

    ```
    int32 my_int
    string full_name "John Doe"
    int32[] samples [-200, -100, 0, 100, 200]
    int32 EXAMPLE=-123
    ```

    """

    name = GObject.Property(type=str, default="")

    python_type = GObject.Property(type=str, default="")
    dds_type = GObject.Property(type=str, default="")
    default_value = GObject.Property(type=str, default="")
    constant = GObject.Property(type=bool, default=False)
    nested_interface_full_name = GObject.Property(type=str, default="")

    field_obj = GObject.Property(type=object, default=None)

    def __init__(
        self,
        *,
        name: str,
        field_obj: object,
        dds_type: str,
        default_value: str = "",
        nested_interface_full_name: str = "",
    ):
        super().__init__()
        self.name = name
        self.field_obj = field_obj
        self.dds_type = dds_type
        self.python_type = field_obj.__class__.__name__
        self.default_value = default_value
        self.nested_interface_full_name = nested_interface_full_name

        if re.match(r"^([A-Z]+(?:_|[A-Z]|[0-9])*)+", self.name):
            self.constant = True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: '{self.name}: {self.python_type}'>"


class InterfaceTypeItem(GObject.GObject):
    __gtype_name__ = "InterfaceTypeItem"
    __item_type__ = "Interface"

    package = GObject.Property(type=str, default="")
    interface_class = GObject.Property(type=str, default="")
    name = GObject.Property(type=str, default="")

    rosidl_obj = GObject.Property(type=object, default=None)

    def __init__(self, *, full_name: str = "", rosidl_obj: object = None, **kwargs):
        super().__init__(**kwargs)
        self._loaded = False

        if full_name != "":
            self.package, self.interface_class, self.name = full_name.split("/")

        elif rosidl_obj is not None:
            self.rosidl_obj = rosidl_obj
            self.package, self.interface_class, self.name = rosidl_obj.__class__.__name__.split(".")
            self._loaded = True

        # self.fields = Gio.ListStore.new(GObject.GObject)

    @GObject.Property(type=str)
    def full_name(self) -> str:
        return f"{self.package}/{self.interface_class}/{self.name}"

    def import_rosidl_obj(self):
        # TODO move this into the ros2 connector?
        raise NotImplementedError("This should be implemented by a child class")

    def ensure_loaded(self):
        if self._loaded:
            return

        self.import_rosidl_obj()
        self._loaded = True

    @staticmethod
    def parse_rosidl_obj(rosidl_obj) -> Gio.ListStore:
        from rosidl_parser.definition import (
            NamespacedType,
            UnboundedSequence,
            BoundedSequence,
            Array,
            BoundedString,
            UnboundedString,
            BoundedWString,
            UnboundedWString,
            BasicType,
        )

        if rosidl_obj is None:
            return Gio.ListStore.new(GObject.GObject)

        fields = Gio.ListStore.new(GObject.GObject)

        def _nested_interface_full_name(slot_type) -> str:
            if hasattr(slot_type, "namespaced_name"):
                return "/".join(slot_type.namespaced_name())
            return ""

        # Iterate through the message fields
        for (field_name, field_type), slot_type in zip(
            rosidl_obj.get_fields_and_field_types().items(),
            rosidl_obj.SLOT_TYPES,
        ):
            field_obj = getattr(rosidl_obj, field_name)  # for builtin types, this is the value

            # for nested messages
            if isinstance(slot_type, NamespacedType):
                field = FieldItem(
                    name=field_name,
                    field_obj=field_obj,
                    dds_type=field_type,  # eg 'uint32'
                    nested_interface_full_name=_nested_interface_full_name(slot_type),
                )
                fields.append(field)

            # for numpy arrays
            # TODO this is still untested, as i cannot refind a msg type with a numpy array, but i swear ive seen one
            # elif isinstance(slot_type, np.ndarray):
            #     row = Adw.ExpanderRow(title=field_name, subtitle=field_type)
            #     row.add(PrefRow(title="Shape", suffix_lbl=field_value.shape))
            #     row.add(PrefRow(title="Dimensions", suffix_lbl=field_value.ndim))
            #     row.add(PrefRow(title="Data Type", suffix_lbl=field_value.dtype))
            #     row.add(PrefRow(title="Size", suffix_lbl=field_value.size))
            #     row.add(PrefRow(title="Value", suffix_lbl=field_value))

            # for sequences of defined lengths
            elif isinstance(slot_type, (UnboundedSequence, BoundedSequence)):
                nested_interface_full_name = ""
                if not isinstance(
                    slot_type.value_type, (BasicType, BoundedString, UnboundedString, BoundedWString, UnboundedWString)
                ):
                    nested_interface_full_name = _nested_interface_full_name(slot_type.value_type)

                field = FieldItem(
                    name=field_name,
                    field_obj=field_obj,
                    dds_type=field_type,
                    nested_interface_full_name=nested_interface_full_name,
                )
                fields.append(field)

            # for arrays
            elif isinstance(slot_type, Array):
                nested_interface_full_name = _nested_interface_full_name(slot_type.value_type)

                # Remove brackets and split the list
                content = str(field_obj).strip("[]").split()
                total_count = len(content)

                if len(field_obj) <= 6:
                    field_obj = str(field_obj)
                else:
                    field_obj = f"[{content[0]} {content[1]} ... {content[-2]} {content[-1]}] <i>x{total_count}</i>"

                field = FieldItem(
                    name=field_name,
                    field_obj=field_obj,
                    dds_type=field_type,
                    nested_interface_full_name=nested_interface_full_name,
                )
                fields.append(field)

            # for strings
            elif isinstance(slot_type, (BoundedString, UnboundedString, BoundedWString, UnboundedWString)):
                field = FieldItem(
                    name=field_name,
                    field_obj=field_obj,
                    dds_type=field_type,
                    default_value=field_obj,
                )
                fields.append(field)

            # for basic types
            elif isinstance(slot_type, BasicType):
                field = FieldItem(
                    name=field_name,
                    field_obj=field_obj,
                    dds_type=field_type,
                    default_value=field_obj,
                )
                fields.append(field)

        return fields

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: '{self.full_name}'>"


class TopicInterfaceTypeItem(InterfaceTypeItem):
    __gtype_name__ = "TopicInterfaceTypeItem"
    __item_type__ = "Topic Interface <msg>"

    msg_fields = GObject.Property(type=object, default=None)

    def __init__(self, full_name: str):
        super().__init__(full_name=full_name)

        if self.interface_class != "msg":
            raise ValueError(
                f"Invalid interface type for TopicInterfaceTypeItem: {self.interface_class}, should be 'msg'"
            )

        self.msg_fields = None

    def ensure_loaded(self):
        if self._loaded:
            return

        super().ensure_loaded()
        self.msg_fields = self.parse_rosidl_obj(self.rosidl_obj)

    def import_rosidl_obj(self):
        try:
            from rosidl_runtime_py.utilities import get_message

            rosidl_class = get_message(self.full_name)
            self.rosidl_obj = rosidl_class()
        except Exception as e:
            _log(f"Failed to load python class for message '{self.full_name}': {e}", level="error")
            raise e


class ServiceInterfaceTypeItem(InterfaceTypeItem):
    __gtype_name__ = "ServiceInterfaceTypeItem"
    __item_type__ = "Service Interface <srv>"

    request_fields = GObject.Property(type=object, default=None)
    response_fields = GObject.Property(type=object, default=None)

    def __init__(self, full_name: str):
        super().__init__(full_name=full_name)
        if self.interface_class != "srv":
            raise ValueError(
                f"Invalid interface type for ServiceInterfaceTypeItem: {self.interface_class}, should be 'srv'"
            )

        self.request_fields = None
        self.response_fields = None

    def ensure_loaded(self):
        if self._loaded:
            return

        super().ensure_loaded()
        self.request_fields = self.parse_rosidl_obj(getattr(self, "request_rosidl_obj", None))
        self.response_fields = self.parse_rosidl_obj(getattr(self, "response_rosidl_obj", None))

    def import_rosidl_obj(self):
        try:
            from rosidl_runtime_py.utilities import get_service

            rosidl_class = get_service(self.full_name)
            self.request_rosidl_obj = rosidl_class.Request()
            self.response_rosidl_obj = rosidl_class.Response()
        except Exception as e:
            _log(f"Failed to resolve service class for '{self.full_name}': {e}", level="error")
            raise e


class ActionInterfaceTypeItem(InterfaceTypeItem):
    __gtype_name__ = "ActionInterfaceTypeItem"
    __item_type__ = "Action Interface <action>"

    goal_fields = GObject.Property(type=object, default=None)
    feedback_fields = GObject.Property(type=object, default=None)
    result_fields = GObject.Property(type=object, default=None)

    def __init__(self, full_name: str):
        super().__init__(full_name=full_name)
        if self.interface_class != "action":
            raise ValueError(
                f"Invalid interface type for ActionInterfaceTypeItem: {self.interface_class}, should be 'action'"
            )

        self.goal_fields = None
        self.feedback_fields = None
        self.result_fields = None

    def ensure_loaded(self):
        if self._loaded:
            return

        super().ensure_loaded()
        self.goal_fields = self.parse_rosidl_obj(getattr(self, "goal_rosidl_obj", None))
        self.feedback_fields = self.parse_rosidl_obj(getattr(self, "feedback_rosidl_obj", None))
        self.result_fields = self.parse_rosidl_obj(getattr(self, "result_rosidl_obj", None))

    def import_rosidl_obj(self):
        try:
            from rosidl_runtime_py.utilities import get_action

            rosidl_class = get_action(self.full_name)
            self.goal_rosidl_obj = rosidl_class.Goal()
            self.feedback_rosidl_obj = rosidl_class.Feedback()
            self.result_rosidl_obj = rosidl_class.Result()
        except Exception as e:
            _log(f"Failed to resolve action class for '{self.full_name}': {e}", level="error")
            raise e


# p = TopicInterfaceTypeItem("geometry_msgs/msg/Pose")
