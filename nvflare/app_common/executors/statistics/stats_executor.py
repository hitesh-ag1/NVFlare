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

from abc import ABC
from typing import Dict

from nvflare.apis.fl_constant import ReservedKey
from nvflare.apis.fl_context import FLContext
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal
from nvflare.app_common.app_constant import StatisticsConstants as StatsConstant
from nvflare.app_common.executors.statistics.base_statistics_executor import BaseStatsExecutor
from nvflare.app_common.executors.statistics.variance_executor import VarExecutor
from nvflare.app_common.executors.statistics.std_histogram import StdHistogramExecutor
from nvflare.app_common.executors.statistics.quantile_histogram import QuantileHistogramExecutor


class StatsExecutor(BaseStatsExecutor, ABC):
    def __init__(
            self,
            executors: Dict[str, BaseStatsExecutor] = {},
            task_name: str = StatsConstant.BASIC_STATS_TASK,
    ):
        super().__init__()
        self.task_name = task_name
        self.executors = executors

    def load_data(self, task_name: str, client_name, fl_ctx: FLContext):
        pass

    def client_exec(self, task_name: str, shareable: Shareable, fl_ctx: FLContext, abort_signal: Signal):
        client_name = fl_ctx.get_prop(ReservedKey.CLIENT_NAME)
        self.log_info(fl_ctx, f"Executing task '{task_name}' for client: '{client_name}'")
        data = self.load_data(task_name, client_name, fl_ctx)
        for task_name in self.executors:
            client_exec : BaseStatsExecutor = self.executors[task_name]
            client_exec.set_data(data)
            if task_name == StatsConstant.COUNT_TASK:
                client_exec.execute(task_name, Shareable(), fl_ctx, abort_signal)
            elif task_name == StatsConstant.MEAN_TASK:
                client_exec.execute(task_name, Shareable(), fl_ctx, abort_signal)
            elif task_name == StatsConstant.VAR_TASK:
                global_mean = shareable['global_mean']
                client_exec : VarExecutor = VarExecutor(client_exec)
                client_exec.set_global_mean(global_mean)
                client_exec.execute(task_name, Shareable(), fl_ctx, abort_signal)
            elif task_name == StatsConstant.STD_HIST_TASK:
                bins = shareable['bins']
                global_bin_range = shareable['global_bin_range']
                client_exec: StdHistogramExecutor = StdHistogramExecutor(client_exec)
                client_exec.set_bins(bins)
                client_exec.set_global_bin_range(global_bin_range)
                client_exec.execute(task_name, Shareable(), fl_ctx, abort_signal)
            elif task_name == StatsConstant.QUAN_HIST_TASK:
                bins = shareable['bins']
                client_exec: QuantileHistogramExecutor = QuantileHistogramExecutor(client_exec)
                client_exec.set_bins(bins)
                client_exec.execute(task_name, Shareable(), fl_ctx, abort_signal)

