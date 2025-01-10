
def is_between(value: float, lower: float, upper: float, incl_lower: bool = True, incl_upper: bool = True) -> bool:
    """Check if a value is in between a lower and an upper boundary. Whether the boundaries itself are included can be
    specified.

    :param value: value to check
    :param lower: lower boundary
    :param upper: upper boundary
    :param incl_lower: whether to include (<=) the lower boundary (vs exclude: <), defaults to True
    :param incl_upper: whether to include (>=) the upper boundary (vs exclude: >), defaults to True
    :return: whether the value is in between the boundary
    """
    if incl_lower:
        lower_check = lower <= value
    else:
        lower_check = lower < value

    if incl_upper:
        upper_check = value <= upper
    else:
        upper_check = value < upper

    return lower_check and upper_check


def clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a value between two boundaries.

    :param value: number that will be clamped
    :param lower: lower boundary of the clamping
    :param upper: upper boundary of the clamping
    :return: clamped value
    """
    return max(lower, min(value, upper))
