# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import threading
import time
from abc import ABC
from threading import Lock
from typing import List, Optional, Tuple, Union

from nvflare.apis.client import Client
from nvflare.apis.controller_spec import ClientTask, ControllerSpec, SendOrder, Task, TaskCompletionStatus
from nvflare.apis.fl_constant import FLContextKey, ReservedTopic
from nvflare.apis.fl_context import FLContext
from nvflare.apis.responder import Responder
from nvflare.apis.server_engine_spec import ServerEngineSpec
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal
from nvflare.security.logging import secure_format_exception
from nvflare.widgets.info_collector import GroupInfoCollector, InfoCollector

from .any_relay_manager import AnyRelayTaskManager
from .bcast_manager import BcastForeverTaskManager, BcastTaskManager
from .operator import Operator
from .send_manager import SendTaskManager
from .seq_relay_manager import SequentialRelayTaskManager
from .task_manager import TaskCheckStatus, TaskManager
from nvflare.apis.fl_context import FLContext


class Broadcast(Operator):

    def __init__(self, fl_ctx: FLContext, task_check_period=0.5):
        """Manage life cycles of tasks and their destinations.

        Args:
            task_check_period (float, optional): interval for checking status of tasks. Defaults to 0.5.
        """
        super().__init__()
        self._engine = None
        self._client_task_map = {}  # client_task_id => client_task
        self._all_done = False
        self._task_check_period = task_check_period
        self.fl_ctx = fl_ctx

    def op(self, parameters: dict, result_received_cb: callable):
        self.validate_inputs(parameters)

        task_name = self.get_task_name(parameters)
        data = self.prepare_shareable(parameters)
        timeout = self.get_timeout(parameters)
        targets = self.get_target_clients(parameters)
        min_responses = self.get_min_responses(parameters)
        wait_time_after_min_received = self.get_wait_time_after_min_clients_received(parameters)
        op_task = Task(
            name=task_name,
            data=data,
            props={},
            timeout=timeout,
            result_received_cb=result_received_cb,
        )
        self.broadcast(op_task, self.fl_ctx, targets, min_responses, wait_time_after_min_received)

    def broadcast(
            self,
            task: Task,
            fl_ctx: FLContext,
            # targets: Union[List[Client], List[str], None] = None,
            targets: Optional[List[str], None] = None,
            min_responses: int = 1,
            wait_time_after_min_received: int = 0,
    ):
        """Schedule a broadcast task.  This is a non-blocking call.

        The task is scheduled into a task list.  Clients can request tasks and controller will dispatch the task to eligible clients.

        Args:
            task (Task): the task to be scheduled
            fl_ctx (FLContext): FLContext associated with this task
            targets (Union[List[Client], List[str], None], optional): the list of eligible clients or client names or None (all clients). Defaults to None.
            min_responses (int, optional): the condition to mark this task as completed because enough clients respond with submission. Defaults to 1.
            wait_time_after_min_received (int, optional): a grace period for late clients to contribute their submission.  0 means no grace period.
              Submission of late clients in the grace period are still collected as valid submission. Defaults to 0.

        Raises:
            ValueError: min_responses is greater than the length of targets since this condition will make the task, if allowed to be scheduled, never exit.
        """
        if targets and min_responses > len(targets):
            raise ValueError(
                "min_responses ({}) must be less than length of targets ({}).".format(min_responses, len(targets))
            )

        manager = BcastTaskManager(
            task=task, min_responses=min_responses, wait_time_after_min_received=wait_time_after_min_received
        )
        self._schedule_task(task=task, fl_ctx=fl_ctx, manager=manager, targets=targets)

    def prepare_shareable(self, parameters: dict):
        return Shareable()

    def get_timeout(self, parameters: dict) -> int:
        timeout = parameters.get("nvflare.task.timeout", 10)
        return timeout

    def get_before_task_cb(self, parameters):
        before_task_cb_lambda = parameters.get("nvflare.task.before_task_cb", None)
        before_task_cb = b" need some work"
        return before_task_cb

    def get_result_received_cb(self, parameters):
        after_task_cb_lambda = parameters.get("nvflare.task.result_received_cb", None)
        after_task_cb = b" need some work"
        return after_task_cb

    def get_target_clients(self, parameters):
        targets: List[str] = parameters.get("nvflare.task.client.targets", None)
        return targets

    def get_min_responses(self, parameters):
        return parameters.get("nvflare.task.client.min_responses", 1)

    def get_wait_time_after_min_clients_received(self, parameters):
        return parameters.get("nvflare.task.wait_time_after_min_received", 0)

    def get_task_name(self, parameters):
        return parameters.get("nvflare.task.name", None)

    def validate_inputs(self, parameters):
        pass
