import time


def has_exceeded_timeout(started_at: time, max_seconds: int) -> bool:
    now = time.time()
    return now > started_at + max_seconds
