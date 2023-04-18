from typing import List

from dstack.backend.base import Backend
from dstack.core.job import JobHead


def poll_logs(
    backend: Backend,
    job_heads: List[JobHead],
    start_time: int,
    attach: bool,
    from_run: bool = False,
):
    try:
        for event in backend.poll_logs(job_heads, start_time, attach):
            print(event.log_message)
    except KeyboardInterrupt as e:
        if attach is True:
            # The only way to exit from the --attach is to Ctrl-C. So
            # we should exit the iterator rather than having the
            # KeyboardInterrupt propagate to the rest of the command.
            if from_run:
                raise e
