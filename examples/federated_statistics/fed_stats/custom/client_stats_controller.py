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
from feature_stats.proto_stats_utils import (
    add_client_stats_to_proto,
    get_aggr_basic_num_stats,
    get_medians,
    get_aggr_avg_str_lens,
    get_common_stats
)
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.controller import Task
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal
from task_controller import TaskController


class ClientStatsController(TaskController):
    def __init__(self):
        super().__init__()
        self.proto = None
        self.task_name = FOConstants.CLIENT_STATS_TASK

    def set_proto(self, proto):
        self.proto = proto

    def task_control_flow(self, abort_signal: Signal, fl_ctx: FLContext) -> bool:
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow started.")
        if abort_signal.triggered:
            return False
        clients = fl_ctx.get_engine().get_clients()
        task = Task(name=self.task_name, data=Shareable(), result_received_cb=self.task_results_cb)
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
        self.controller.log_info(fl_ctx, f"task_post_fn for task {task_name}")
        self.save_client_stats_to_proto()

        # prepare sharable data
        aggr_means, agg_counts, total_count, aggr_mins, aggr_maxs, aggr_zeros = \
            get_aggr_basic_num_stats(self.result)

        medians = get_medians(self.result)
        self.shareable.update(
            {FOConstants.AGGR_MEANS: aggr_means,
             FOConstants.AGGR_COUNTS: agg_counts,
             FOConstants.AGGR_ZEROS: aggr_zeros,
             FOConstants.AGGR_MINS: aggr_mins,
             FOConstants.AGGR_MAXES: aggr_maxs,
             FOConstants.TOTAL_COUNT: total_count,
             FOConstants.CLIENT_MEDIANS: medians
             }
        )

    def populate_feature_names(self):
        feature_names = []
        for i, client_name in enumerate(self.result):
            if i == 0:
                feature_names = [feature_name for feature_name in self.result[client_name]]
        self.shareable.update({"feature_names": feature_names})

    def save_client_stats_to_proto(self):
        proto_stats = self.proto
        for client_name in self.result:
            add_client_stats_to_proto(client_name, proto_stats, self.result)

    def get_common_stats(self):
        return get_common_stats(self.result)

    def get_aggr_basic_num_stats(self):
        return get_aggr_basic_num_stats(self.result)

    def get_aggr_avg_str_lens(self):
        return get_aggr_avg_str_lens(self.result)

    def get_aggr_means(self) -> Union[Dict[str, float], None]:
        return self.get_aggr_dicts(FOConstants.AGGR_MEANS)

    def get_aggr_counts(self) -> Union[Dict[str, int], None]:
        return self.get_aggr_dicts(FOConstants.AGGR_COUNTS)

    def get_total_count(self) -> int:
        return self.get_aggr_int_values(FOConstants.TOTAL_COUNT)

    def get_client_medians(self) -> Union[Dict[str, int], None]:
        return self.get_aggr_dicts(FOConstants.CLIENT_MEDIANS)

    def get_aggr_zeros(self) -> Union[Dict[str, int], None]:
        return self.get_aggr_dicts(FOConstants.AGGR_ZEROS)

    def get_aggr_maxs(self) -> Union[Dict[str, int], None]:
        return self.get_aggr_dicts(FOConstants.AGGR_MAXES)

    def get_aggr_mins(self) -> Union[Dict[str, int], None]:
        return self.get_aggr_dicts(FOConstants.AGGR_MINS)

    def get_aggr_missings(self) -> Union[Dict[str, int], None]:
        return self.get_aggr_dicts(FOConstants.AGGR_MISSINGs)

    def get_aggr_dicts(self, key: str) -> Union[Dict[str, int], None]:
        if key in self.shareable:
            return self.shareable[key]
        else:
            return None

    def get_aggr_int_values(self, key: str) -> int:
        if key in self.shareable:
            return self.shareable[key]
        else:
            return 0
