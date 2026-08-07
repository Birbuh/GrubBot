import socket


class UnauthorizedHostError(Exception):
    """Raised when the bot is started from an unrecognized host."""

    def __init__(self):
        """Initialize the error and terminate the process."""
        super().__init__("This device is unrecognized")
        print("This device is unrecognized! Oops!")
        quit()


def os_recog() -> tuple[bool, str]:
    """Return whether this is the stable host and its command prefix."""
    host_name = socket.gethostname()
    if host_name == "archlinux":
        is_stable = False
    else:
        is_stable = True

    if is_stable:
        bot_prefix = "?"
    else:
        bot_prefix = "??"

    return is_stable, bot_prefix
