# Copyright (c) 2022, NVIDIA CORPORATION.
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
from abc import ABC
from typing import Union

from feature_stats.feature_stats_constants import FeatureStatsConstants
from feature_stats.feature_stats_def import (
    DatasetStatisticsList,
)
from nvflare.apis.dxo import from_shareable
from nvflare.apis.fl_constant import ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.controller import ClientTask, Controller
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal


class TaskController(ABC):
    def __init__(self):
        self.controller = None
        self.rc = ReturnCode.EMPTY_RESULT
        self.result = {}
        self.task_name: Union[str, None] = None
        self.shareable = Shareable()

    def set_controller(self, controller: Controller):
        self.controller = controller

    def task_control_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        pass

    def get_return_code(self):
        return self.rc

    def task_results_cb(self, client_task: ClientTask, fl_ctx: FLContext):
        client_name = client_task.client.name
        task_name = client_task.task.name
        self.controller.log_info(fl_ctx, f"Processing {task_name} result from client {client_name}")
        result = client_task.result
        rc = result.get_return_code()
        self.rc = rc

        if rc == ReturnCode.OK:
            dxo = from_shareable(result)
            data_stats_dict = dxo.data
            data_kind = dxo.data_kind
            self.controller.log_info(fl_ctx,
                                     f"Received result entries {data_stats_dict.keys()}, data_kind = {data_kind}")
            import base64
            import pickle

            print(f"client_task.task.name={client_task.task.name}")
            print(f"task.name={self.task_name}")

            if client_task.task.name == self.task_name:
                encoded_stats = data_stats_dict[FeatureStatsConstants.STATS]
                stats: DatasetStatisticsList = pickle.loads(base64.decodebytes(encoded_stats))
                self.result[client_name] = {FeatureStatsConstants.STATS: stats}
            else:
                self.controller.log_info(fl_ctx,
                                         f"task_name:{self.task_name} is not the same as ${client_task.task.name}")

        else:
            self.controller.log_info(
                fl_ctx, f"Ignore the client  {client_name} result. {task_name} tasked returned error code: {rc}"
            )

        # Cleanup task result
        client_task.result = None
