import socket


class UnauthorizedHostError(Exception):
    def __init__(self):
        super().__init__("This device is unrecognized")
        print("This device is unrecognized! Oops!")
        quit()


def os_recog() -> tuple[bool, str]:
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
