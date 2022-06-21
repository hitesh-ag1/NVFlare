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
import logging
from typing import Dict, Optional

from client_stats_controller import ClientStatsController
from facets_overview_constants import FOConstants
from feature_stats import feature_statistics_pb2 as fs
from feature_stats.feature_statistics_pb2 import DatasetFeatureStatisticsList as ProtoDatasetFeatureStatisticsList
from feature_stats.feature_statistics_pb2 import Histogram as ProtoHistogram
from feature_stats.feature_stats_def import (
    CommonStatistics,
)
from feature_stats.proto_stats_utils import (
    copy_proto_histogram
)
from global_histogram_controller import GlobalHistogramController
from global_median_controller import GlobalMedianController
from global_variance_controller import GlobalVarianceController
from nvflare.apis.client import Client
from nvflare.apis.fl_constant import FLContextKey, ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.controller import Controller
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal


class FacetsOverviewController(Controller):
    def __int__(self):
        self.proto = None

    @property
    def task_name(self):
        return "fed_stats"

    def control_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        controller = self
        controller.proto = ProtoDatasetFeatureStatisticsList()
        client_sc = ClientStatsController()
        rc = self.run_client_stats_flow(abort_signal, client_sc, controller, fl_ctx)

        if rc == ReturnCode.OK:
            aggr_means, aggr_counts, total_count, aggr_mins, aggr_maxs, aggr_zeros \
                = client_sc.get_aggr_basic_num_stats()
            client_medians = client_sc.get_client_medians()

            global_vc = GlobalVarianceController()
            rc = self.run_variance_flow(abort_signal, aggr_counts, aggr_means, controller, fl_ctx, global_vc)

            if rc == ReturnCode.OK:
                aggr_std_devs = global_vc.get_aggr_std_dev()
                # update std_devs for protos
                global_mc = GlobalMedianController()
                rc = self.run_median_flow(abort_signal, aggr_counts, client_medians, controller, fl_ctx, global_mc)

                if rc == ReturnCode.OK:
                    # get numeric stats histograms
                    global_hc = GlobalHistogramController()
                    rc = self.run_histogram_flow(abort_signal, aggr_maxs, aggr_mins, controller, fl_ctx, global_hc)

                    if rc == ReturnCode.OK:
                        aggr_medians = global_mc.get_pivots()
                        src_common_stats = client_sc.get_common_stats()
                        self._populate_global_stats(global_hc,
                                                    aggr_medians=aggr_medians,
                                                    aggr_std_devs=aggr_std_devs,
                                                    aggr_avg_str_lens=client_sc.get_aggr_avg_str_lens(),
                                                    aggr_means=aggr_means,
                                                    aggr_mins=aggr_mins,
                                                    aggr_maxs=aggr_maxs,
                                                    aggr_zeros=aggr_zeros,
                                                    total_count=total_count,
                                                    src_common_stats=src_common_stats)

                    else:
                        logging.error(f"no result returned for numeric stats {global_hc.task_name} ")

                        # get common stats histograms
                    # get string stats histograms

                else:
                    logging.error(f"no result returned for {global_mc.task_name} ")
            else:
                logging.error(f"no result returned for {global_vc.task_name} ")

            self._save_result_to_file(fl_ctx)
        else:
            logging.error(f"no result returned for {client_sc.task_name} ")

    def run_histogram_flow(self, abort_signal, aggr_maxs, aggr_mins, controller, fl_ctx, global_hc):
        h_shareable = Shareable()
        h_shareable.update({FOConstants.AGGR_MINS: aggr_mins, FOConstants.AGGR_MAXES: aggr_maxs})
        global_hc.set_mins_maxs(h_shareable)
        global_hc.set_controller(controller)
        global_hc.task_control_flow(abort_signal, fl_ctx)
        return global_hc.get_return_code()

    def run_median_flow(self, abort_signal, aggr_counts, client_medians, controller, fl_ctx, global_mc):
        global_mc.set_controller(controller)
        global_mc.set_counts(aggr_counts)
        global_mc.set_client_medians(client_medians)
        global_mc.task_control_flow(abort_signal, fl_ctx)
        return global_mc.get_return_code()

    def run_client_stats_flow(self, abort_signal, client_sc, controller, fl_ctx):
        client_sc.set_controller(controller)
        client_sc.set_proto(controller.proto)
        client_sc.task_control_flow(abort_signal, fl_ctx)
        return client_sc.get_return_code()

    def run_variance_flow(self, abort_signal, aggr_counts, aggr_means, controller, fl_ctx, global_vc):
        shareable = Shareable()
        shareable[FOConstants.AGGR_MEANS] = aggr_means
        shareable[FOConstants.AGGR_COUNTS] = aggr_counts
        global_vc.set_controller(controller)
        global_vc.set_sharable(shareable)
        global_vc.task_control_flow(abort_signal, fl_ctx)
        return global_vc.get_return_code()

    def start_controller(self, fl_ctx: FLContext):
        pass

    def stop_controller(self, fl_ctx: FLContext):
        pass

    def process_result_of_unknown_task(self,
                                       client: Client,
                                       task_name: str,
                                       client_task_id: str,
                                       result: Shareable,
                                       fl_ctx: FLContext):
        pass

    def _save_result_to_file(self, fl_ctx: FLContext, file_path: Optional[str] = None):
        import os
        import base64
        from pathlib import Path
        try:
            workspace = fl_ctx.get_prop(FLContextKey.WORKSPACE_OBJECT)
            workspace_dir = workspace.get_root_dir()
            base_dir = os.path.join(workspace_dir, f"{self.task_name}")
            if not file_path:
                result_path = os.path.join(base_dir, f"{self.task_name}.pb")
            else:
                result_path = os.path.join(base_dir, file_path)

            os.makedirs(Path(result_path).parent.absolute(), exist_ok=True)  # check permissions/handle failures

            self.log_info(fl_ctx, f"saving to {result_path}")

            data = base64.b64encode(self.proto.SerializeToString()).decode("utf-8")
            with open(result_path, "w") as text_file:
                text_file.write(data)

        except BaseException as e:
            logging.error(f"failed to save file {e}", exc_info=True)
            raise e

    def _populate_common_stats(self, src_common_stats: CommonStatistics, common_stats):

        common_stats.num_missing = src_common_stats.num_missing
        common_stats.num_non_missing = src_common_stats.num_non_missing
        common_stats.min_num_values = src_common_stats.min_num_values
        common_stats.max_num_values = src_common_stats.max_num_values
        common_stats.avg_num_values = src_common_stats.avg_num_values
        return common_stats

    def _populate_global_stats(self,
                               global_hc: GlobalHistogramController,
                               aggr_medians: dict,
                               aggr_std_devs: dict,
                               aggr_avg_str_lens: dict,
                               aggr_means: dict,
                               aggr_mins: dict,
                               aggr_maxs: dict,
                               aggr_zeros: dict,
                               total_count: int,
                               src_common_stats: Dict[str, CommonStatistics],
                               ):

        # aggr_means, agg_counts, \
        # total_count, aggr_mins, \
        # aggr_maxs, aggr_zeros = client_sc.get_aggr_basic_num_stats()

        proto_ds = self.proto.datasets.add(name="global", num_examples=total_count)

        for src in self.proto.datasets[0].features:
            dest = proto_ds.features.add(type=src.type, name=src.name)

            if src.type == fs.FeatureNameStatistics.INT or src.type == fs.FeatureNameStatistics.FLOAT:
                dest.num_stats.std_dev = aggr_std_devs[src.name]
                dest.num_stats.median = aggr_medians[src.name]
                dest.num_stats.mean = aggr_means[src.name]
                dest.num_stats.min = aggr_mins[src.name]
                dest.num_stats.max = aggr_maxs[src.name]

                dest.num_stats.num_zeros = aggr_zeros[src.name]
                common_stats = dest.num_stats.common_stats
                self._populate_common_stats(src_common_stats[src.name], common_stats)

                for histograms in global_hc.get_histograms():
                    for hist_type in histograms:
                        hp = histograms[hist_type][src.name]
                        proto_hist: ProtoHistogram = dest.num_stats.histograms.add()
                        copy_proto_histogram(hp, proto_hist)

            elif src.type == fs.FeatureNameStatistics.STRING:
                common_stats = dest.string_stats.common_stats
                self._populate_common_stats(src_common_stats[src.name], common_stats)

                # this is not correct, but not sure how to do it correctly without
                # knowing the overall dataset. also AttributeError: unique_vals
                # dest.string_stats.unique_vals += src.string_stats.unique_vals                #
                # AttributeError: Assignment not allowed to repeated field "top_values" in protocol message object.
                # dest.string_stats.top_values = []  # we can't review user's data
                dest.string_stats.avg_length += aggr_avg_str_lens[src.name]
                # todo we might be able to do the global rank bt combined unique values
                # AttributeError: Assignment not allowed to field "rank_histogram" in protocol message object
                # dest.string_stats.rank_histogram = None
        #
        # self._print_age_histogram()

        return proto_ds
