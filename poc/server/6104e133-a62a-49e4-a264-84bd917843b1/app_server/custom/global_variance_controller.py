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
from typing import Dict, Union

from facets_overview_constants import FOConstants
from feature_stats.feature_stats_constants import FeatureStatsConstants
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.controller import Task
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal
from task_controller import TaskController


class GlobalVarianceController(TaskController):
    def __int__(self):
        super().__init__()
        # why this is not always work
        self.task_name = FOConstants.AGGR_VAR_TASK
        self.shareable = Shareable()

    def set_sharable(self, shareable: Shareable):
        self.shareable = shareable

    def task_control_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        self.task_name = FOConstants.AGGR_VAR_TASK

        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow started.")
        if abort_signal.triggered:
            return
        clients = fl_ctx.get_engine().get_clients()
        task = Task(name=self.task_name, data=self.shareable, result_received_cb=self.task_results_cb)
        self.controller.broadcast_and_wait(
            task=task,
            targets=None,
            min_responses=len(clients),
            fl_ctx=fl_ctx,
            wait_time_after_min_received=1,
            abort_signal=abort_signal,
        )
        self.task_post_fn(self.task_name, fl_ctx)
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow end.")

    def task_post_fn(self, task_name: str, fl_ctx: FLContext):
        self.controller.log_info(fl_ctx, f"in task_post_fn for task {task_name}")
        aggr_variances = {}
        for client_name in self.result:
            aggr_vars = self.result[client_name][FeatureStatsConstants.STATS]
            feature_vars = aggr_vars[FOConstants.AGGR_VARS]
            for feat in feature_vars:
                if feat in aggr_variances:
                    aggr_variances[feat] = feature_vars[feat] + aggr_variances[feat]
                else:
                    aggr_variances[feat] = feature_vars[feat]
        import math

        agg_std_dev = {}
        for feat in aggr_variances:
            agg_std_dev[feat] = math.sqrt(aggr_variances[feat])

        self.shareable[FOConstants.AGGR_STDDEV] = agg_std_dev

    def get_aggr_std_dev(self) -> Union[Dict[str, float], None]:
        if FOConstants.AGGR_STDDEV in self.shareable:
            return self.shareable[FOConstants.AGGR_STDDEV]
        else:
            return None
