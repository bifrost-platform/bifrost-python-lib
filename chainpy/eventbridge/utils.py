import time


# TODO convert sec instead of msec
def timestamp_msec() -> int:
    return int(time.time() * 1000)
