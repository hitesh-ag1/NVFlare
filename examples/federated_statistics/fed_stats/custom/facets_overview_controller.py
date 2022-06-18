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
import os
from abc import ABC
from typing import Dict, List, NamedTuple, Optional, Union

from facets_overview_constants import FOConstants
from feature_stats import feature_statistics_pb2 as fs
from feature_stats.feature_statistics_pb2 import CommonStatistics as ProtoCommonStatistics
from feature_stats.feature_statistics_pb2 import CustomStatistic as ProtoCustomStatistic
from feature_stats.feature_statistics_pb2 import DatasetFeatureStatistics as ProtoDatasetFeatureStatistics
from feature_stats.feature_statistics_pb2 import DatasetFeatureStatisticsList as ProtoDatasetFeatureStatisticsList
from feature_stats.feature_statistics_pb2 import FeatureNameStatistics as ProtoFeatureNameStatistics
from feature_stats.feature_statistics_pb2 import Histogram as ProtoHistogram
from feature_stats.feature_statistics_pb2 import NumericStatistics as ProtoNumericStatistics
from feature_stats.feature_statistics_pb2 import RankHistogram as ProtoRankHistogram
from feature_stats.feature_statistics_pb2 import StringStatistics as ProtoStringStatistics
from feature_stats.feature_stats_constants import FeatureStatsConstants
from feature_stats.feature_stats_def import (
    BasicNumStats,
    Bucket,
    CommonStatistics,
    DatasetStatistics,
    DatasetStatisticsList,
    DataType,
    FeatureStatistics,
    FreqAndValue,
    Histogram,
    HistogramType,
    NumericStatistics,
    RankBucket,
    RankHistogram,
    StringStatistics,
)
from feature_stats.proto_stats_utils import (
    add_client_stats_to_proto,
    get_aggr_basic_num_stats,
    get_medians,
    get_aggr_avg_str_lens
)

from nvflare.apis.client import Client
from nvflare.apis.dxo import from_shareable
from nvflare.apis.fl_constant import FLContextKey, ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.controller import ClientTask, Controller, Task
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal

from task_controller import TaskController
from client_stats_controller import ClientStatsController
from global_variance_controller import GlobalVarianceController
from global_median_controller import GlobalMedianController
from global_histogram_controller import GlobalHistogramController


class FacetsOverviewController(Controller):
    def __int__(self):
        self.proto = None
        self.task_name = "fed_stats"

    def control_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        controller = self
        controller.proto = ProtoDatasetFeatureStatisticsList()
        client_stats_controller = ClientStatsController()
        client_stats_controller.set_controller(controller)
        client_stats_controller.set_proto(controller.proto)

        client_stats_controller.task_control_flow(abort_signal, fl_ctx)
        rc = client_stats_controller.get_return_code()
        if rc == ReturnCode.OK:
            #
            # aggr_means = client_stats_controller.get_aggr_means()
            # aggr_counts = client_stats_controller.get_aggr_counts()
            # client_medians = client_stats_controller.get_client_medians()
            #
            # shareable = Shareable()
            # shareable[FOConstants.AGGR_MEANS] = aggr_means
            # shareable[FOConstants.AGGR_COUNTS] = aggr_counts
            #
            # aggr_var_controller = GlobalVarianceController()
            # aggr_var_controller.set_controller(controller)
            # aggr_var_controller.set_sharable(shareable)
            # aggr_var_controller.task_control_flow(abort_signal, fl_ctx)
            # rc = aggr_var_controller.get_return_code()
            # if rc == ReturnCode.OK:
            #     aggr_std_devs = aggr_var_controller.get_aggr_std_dev()
            #     # update std_devs for protos
            #     aggr_median_controller = GlobalMedianController()
            #     aggr_median_controller.set_controller(controller)
            #
            #     aggr_median_controller.set_counts(aggr_counts)
            #     aggr_median_controller.set_client_medians(client_medians)
            #     rc = aggr_median_controller.get_return_code()
            #     if rc == ReturnCode.OK:
            #         aggr_median_controller.shareable.update(shareable)
            #         aggr_median_controller.task_control_flow(abort_signal, fl_ctx)
            #
            #         aggr_medians = aggr_median_controller.get_pivots()
            #
            #         aggr_means, agg_counts, \
            #         total_count, aggr_mins, \
            #         aggr_maxs, aggr_zeros, \
            #         aggr_missings = client_stats_controller.get_aggr_basic_num_stats()
            #
            #         src_common_stats = {}
            #         for feat_name in aggr_means:
            #             src_common_stats[feat_name] = CommonStatistics(num_non_missing=agg_counts[feat_name],
            #                                                            num_missing=aggr_missings[feat_name],
            #                                                            min_num_values=aggr_mins[feat_name],
            #                                                            max_num_values=aggr_maxs[feat_name],
            #                                                            avg_num_values=aggr_means[feat_name],
            #                                                            tot_num_values=agg_counts[feat_name])
            #
            #         self._populate_global_stats(total_count=total_count,
            #                                     aggr_medians=aggr_medians,
            #                                     aggr_std_devs=aggr_std_devs,
            #                                     aggr_avg_str_lens=client_stats_controller.get_aggr_avg_str_lens(),
            #                                     src_common_stats=src_common_stats)
            #     else:
            #         logging.error(f"no result returned for {aggr_median_controller.task_name} ")
            # else:
            #     logging.error(f"no result returned for {aggr_var_controller.task_name} ")

            self._save_result_to_file(fl_ctx)
        else:
            logging.error(f"no result returned for {client_stats_controller.task_name} ")

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

            logging.info(f"saving to {result_path}")

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
                               total_count,
                               aggr_medians: dict,
                               aggr_std_devs: dict,
                               aggr_zeros: dict,
                               aggr_avg_str_lens: dict,
                               src_common_stats: Dict[str, CommonStatistics],
                               ):
        proto_ds = controller.proto.datasets.add(name="global", num_examples=total_count)

        for src in controller.proto.datasets[0].features:
            dest = proto_ds.features.add(type=src.type, name=src.name)

            if src.num_stats:
                dest.num_stats.std_dev = aggr_std_devs[src.name]
                dest.num_stats.median = aggr_medians[src.name]
                dest.num_stats.num_zeros = aggr_zeros[src.name]

                dest.num_stats.mean = src_common_stats[src.name].avg_num_values
                dest.num_stats.min = src_common_stats[src.name].min_num_values
                dest.num_stats.max = src_common_stats[src.name].max_num_values

                common_stats = dest.num_stats.common_stats
                self._populate_common_stats(src_common_stats[src.name], common_stats)
                #dest.num_stats.histograms =

            elif src.string_stats:
                common_stats = dest.string_stats.common_stats
                self._populate_common_stats(src_common_stats[src.name], common_stats)

                # this is not correct, but not sure how to do it correctly without
                # knowing the overall dataset.
                dest.string_stats.unique_vals += src.string_stats.unique_vals
                dest.string_stats.top_values = []  # we can't review user's data
                dest.string_stats.avg_length += aggr_avg_str_lens[src.name]
                # todo we might be able to do the global rank bt combined unique values
                dest.string_stats.rank_histogram = None

        return proto_ds
