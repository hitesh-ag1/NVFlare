import time
from abc import ABC
from threading import Lock
from typing import List, Optional

from nvflare.apis.client import Client
from nvflare.apis.controller_spec import Task
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.task_manager import TaskManager
from nvflare.apis.operator_spec import OperatorSpec

# todo move this to a constant file and shared by Controller

_TASK_KEY_ENGINE = "___engine"
_TASK_KEY_MANAGER = "___mgr"
_TASK_KEY_DONE = "___done"


class Operator(OperatorSpec, ABC):

    def __init__(self):
        super().__init__()
        self._task_lock = Lock()
        self._tasks = []  # list of standing tasks

    def _schedule_task(
            self,
            task: Task,
            fl_ctx: FLContext,
            manager: TaskManager,
            targets: Optional[List[str]],
            allow_dup_targets: bool = False,
    ):

        if task.schedule_time is not None:
            # this task was scheduled before
            # we do not allow a task object to be reused
            self.logger.debug("task.schedule_time: {}".format(task.schedule_time))
            raise ValueError("Task was already used. Please create a new task object.")

        task.targets = targets
        if targets is not None:
            target_names = list()
            if not isinstance(targets, list):
                raise ValueError("task targets must be a list, but got {}".format(type(targets)))
            for t in targets:
                if isinstance(t, str):
                    name = t
                elif isinstance(t, Client):
                    name = t.name
                else:
                    raise ValueError("element in targets must be string or Client type, but got {}".format(type(t)))

                if allow_dup_targets or (name not in target_names):
                    target_names.append(name)
            task.targets = target_names

        task.props[_TASK_KEY_MANAGER] = manager
        task.props[_TASK_KEY_ENGINE] = fl_ctx.get_engine()
        task.is_standing = True
        task.schedule_time = time.time()

        with self._task_lock:
            self._tasks.append(task)
            self.log_info(fl_ctx, "scheduled task {}".format(task.name))

