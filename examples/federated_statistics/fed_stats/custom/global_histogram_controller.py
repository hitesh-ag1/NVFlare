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
    HistogramType
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
        min_res = int((len(clients) + 1) / 2)
        self.controller.broadcast_and_wait(
            task=task,
            targets=None,
            min_responses=min_res,
            fl_ctx=fl_ctx,
            wait_time_after_min_received=1,
            abort_signal=abort_signal,
        )
        self.task_post_fn(self.task_name, fl_ctx)
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow end.")

    def task_post_fn(self, task_name: str, fl_ctx: FLContext):
        self.controller.log_info(fl_ctx, f"in task_post_fn for task {task_name}")
        global_std_hists = self._aggregate_global_histogram(HistogramType.STANDARD)
        global_quan_hists = self._aggregate_global_histogram(HistogramType.QUANTILES)

        self.shareable[HistogramType.STANDARD] = global_std_hists
        self.shareable[HistogramType.QUANTILES] = global_quan_hists

    def _aggregate_global_histogram(self, hist_type: HistogramType) -> Dict[HistogramType, Dict[str, Histogram]]:
        temp_hists = {}
        for client_name in self.result:
            histograms = self.result[client_name][FeatureStatsConstants.STATS]
            feature_histograms = histograms[hist_type]
            for feat_name in feature_histograms:
                temp_hists[feat_name] = {}
                hist = feature_histograms[feat_name]
                if "num_nan" in temp_hists[feat_name]:
                    temp_hists[feat_name]["num_nan"] += hist.num_nan
                else:
                    temp_hists[feat_name]["num_nan"] = hist.num_nan

                if "num_undefined" in temp_hists[feat_name]:
                    temp_hists[feat_name]["num_undefined"] += hist.num_undefined
                else:
                    temp_hists[feat_name]["num_undefined"] = hist.num_undefined

                temp_hists[feat_name]["buckets"] = {}
                bs = temp_hists[feat_name]["buckets"]

                for bucket in hist.buckets:
                    if (bucket.low_value, bucket.high_value) in bs:
                        bs[(bucket.low_value, bucket.high_value)] += bucket.sample_count
                    else:
                        bs[(bucket.low_value, bucket.high_value)] = bucket.sample_count

        global_std_hists = {}
        buckets: Dict[str, List[Bucket]] = {}
        for feat_name in temp_hists:
            hist1 = temp_hists[feat_name]
            bs = hist1['buckets']
            buckets[feat_name] = []
            for (l, h) in bs:
                buckets[feat_name].append(Bucket(l, h, bs[(l, h)]))

            global_std_hists[feat_name] = Histogram(num_nan=hist1['num_nan'],
                                                    num_undefined=hist1['num_undefined'],
                                                    buckets=buckets[feat_name],
                                                    hist_type=hist_type)
        return {hist_type: global_std_hists}

    def get_histograms(self):
        return [self.shareable[HistogramType.STANDARD],
                self.shareable[HistogramType.QUANTILES]]
