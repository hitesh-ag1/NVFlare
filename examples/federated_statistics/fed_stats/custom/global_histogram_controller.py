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
from typing import Dict, List

from facets_overview_constants import FOConstants
from feature_stats.feature_stats_constants import FeatureStatsConstants
from feature_stats.feature_stats_def import (
    Bucket,
    Histogram,
)
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.controller import Task
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal
from task_controller import TaskController


class GlobalHistogramController(TaskController):
    def __int__(self):
        super().__init__()
        # why this is not always work
        self.task_name = FOConstants.AGGR_HISTOGRAM_TASK
        self.shareable = Shareable()

    def set_mins_maxs(self, shareable: Shareable):
        self.shareable = shareable

    def task_control_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        self.task_name = FOConstants.AGGR_HISTOGRAM_TASK
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow started.")

        if FOConstants.AGGR_MINS not in self.shareable:
            raise ValueError(f"expected {FOConstants.AGGR_MINS} is not set")
        if FOConstants.AGGR_MAXES not in self.shareable:
            raise ValueError(f"expected {FOConstants.AGGR_MAXES} is not set")

        if abort_signal.triggered:
            return

        clients = fl_ctx.get_engine().get_clients()
        task = Task(name=self.task_name, data=self.shareable, result_received_cb=self.task_results_cb)
        self.controller.broadcast_and_wait(
            task=task,
            targets=None,
            min_responses=len(clients) / 2,
            fl_ctx=fl_ctx,
            wait_time_after_min_received=1,
            abort_signal=abort_signal,
        )
        self.task_post_fn(self.task_name, fl_ctx)
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow end.")

    def task_post_fn(self, task_name: str, fl_ctx: FLContext):
        self.controller.log_info(fl_ctx, f"in task_post_fn for task {task_name}")
        global_std_hists = self._aggregate_global_histogram(FOConstants.STD_HISTOGRAMS)
        global_quan_hists = self._aggregate_global_histogram(FOConstants.QUAN_HISTOGRAMS)

        self.shareable[FOConstants.STD_HISTOGRAMS] = global_std_hists
        self.shareable[FOConstants.QUAN_HISTOGRAMS] = global_quan_hists

    def _aggregate_global_histogram(self, hist_type_key: str) -> Dict[str, Histogram]:
        temp_std_hists = {}
        for client_name in enumerate(self.result):
            histograms = self.result[client_name][FeatureStatsConstants.STATS]
            feature_std_histograms = histograms[hist_type_key]
            for feat_name in feature_std_histograms:
                temp_std_hists[feat_name] = {}
                std_hist = feature_std_histograms[feat_name]
                if "num_nan" in temp_std_hists[feat_name]:
                    temp_std_hists[feat_name]["num_nan"] += std_hist.num_nan
                else:
                    temp_std_hists[feat_name]["num_nan"] = std_hist.num_nan

                if "num_undefined" in temp_std_hists[feat_name]:
                    temp_std_hists[feat_name]["num_undefined"] += std_hist.num_undefined
                else:
                    temp_std_hists[feat_name]["num_undefined"] = std_hist.num_undefined

                temp_std_hists[feat_name]["buckets"] = {}
                bs = temp_std_hists[feat_name]["buckets"]

                for bucket in std_hist.buckets:
                    if (bucket.low_value, bucket.high_value) in bs:
                        bs[(bucket.low_value, bucket.high_value)] += bucket.sample_count
                    else:
                        bs[(bucket.low_value, bucket.high_value)] = bucket.sample_count

        global_std_hists = {}
        for feat_name in temp_std_hists:
            hist = temp_std_hists[feat_name]
            bs = hist['buckets']
            buckets: List[Bucket] = []
            for (l, h) in bs:
                buckets.append(Bucket(l, h, bs[(l, h)]))

            global_std_hists[feat_name] = Histogram(hist['num_nan'], hist['num_undefined'], buckets=buckets)

        return global_std_hists
