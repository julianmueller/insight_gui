import rclpy.logging


def ros_log(message: str, level: str = "info", *, name: str = "insight_gui") -> None:
    logger = rclpy.logging.get_logger(name)
    log_func = getattr(logger, level, logger.info)
    log_func(str(message))
