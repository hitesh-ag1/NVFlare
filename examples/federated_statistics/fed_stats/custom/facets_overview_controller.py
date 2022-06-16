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
from feature_stats.proto_stats_utils import add_client_stats_to_proto, get_aggr_basic_num_stats, get_medians

from nvflare.apis.client import Client
from nvflare.apis.dxo import from_shareable
from nvflare.apis.fl_constant import FLContextKey, ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.controller import ClientTask, Controller, Task
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
        proto_stats = self.proto
        for client_name in self.result:
            print(f"client  = {client_name}")
            add_client_stats_to_proto(client_name, proto_stats, self.result)

        # prepare sharable data
        aggr_means, agg_counts, \
        total_count, aggr_mins, \
        aggr_maxs, aggr_zeros, \
        aggr_missings = get_aggr_basic_num_stats(self.result)

        medians = get_medians(self.result)
        self.shareable.update(
            {FOConstants.AGGR_MEANS: aggr_means,
             FOConstants.AGGR_COUNTS: agg_counts,
             FOConstants.AGGR_ZEROS: aggr_zeros,
             FOConstants.AGGR_MINS: agg_mins,
             FOConstants.AGGR_MAXES: aggr_maxs,
             FOConstants.TOTAL_COUNT: total_count,
             FOConstants.AGGR_MISSINGs: aggr_missings,
             FOConstants.CLIENT_MEDIANS: medians
             }
        )

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


class AggregateVarController(TaskController):
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
            print("client-name", client_name)
            print("aggr_vars=", aggr_vars)

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


class AggregateMedianController(TaskController):
    def __init__(self):
        super().__init__()
        self.feature_counts = {}
        self.client_medians = {}
        self.task_name = FOConstants.AGGR_MEDIAN_TASK

    def set_counts(self, counts: Dict[str, int]):
        self.feature_counts = counts

    def set_client_medians(self, client_medians: dict):
        self.client_medians = client_medians

    def set_k_values(self):
        k_values = {}
        for feat in self.feature_counts:
            k_values[feat] = self.feature_counts[feat] / 2

        self.shareable[FOConstants.K_VALUES] = k_values

    def task_control_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow started.")
        if abort_signal.triggered:
            return
        task_flow_round = 1
        self.set_k_values()
        while not self.stop_actions() and task_flow_round < 2:
            print(f"task {self.task_name} control flow round = {task_flow_round}.")
            print(f"task {self.task_name} control flow round = {task_flow_round}.")
            print(f"task {self.task_name} control flow round = {task_flow_round}.")
            print(f"task {self.task_name} control flow round = {task_flow_round}.")
            print(f"task {self.task_name} k_values = {self.shareable[FOConstants.K_VALUES]}.")
            if FOConstants.PIVOT_SIZES in self.shareable:
                print(f"task {self.task_name} m_values = {self.shareable[FOConstants.PIVOT_SIZES]}.")
                for feat_name in self.shareable[FOConstants.K_VALUES]:
                    m, e, l = self.shareable[FOConstants.PIVOT_SIZES][feat_name]
                    print(f"{feat_name} delta = ", (m + e) - self.shareable[FOConstants.K_VALUES][feat_name])
            else:
                print(f"task {self.task_name} m_values is empty ")

            if FOConstants.MEDIAN_ACTION in self.shareable:
                print(f"task {self.task_name} median action = {self.shareable[FOConstants.MEDIAN_ACTION]}.")
            else:
                print(f"task {self.task_name} median action is empty ")

            self.controller.log_info(fl_ctx, f"task {self.task_name} control flow round = {task_flow_round}.")
            self.shareable.set_header(FOConstants.TASK_FLOW_ROUND, task_flow_round)

            if task_flow_round == 1:
                client = fl_ctx.get_engine().get_clients()[0]
                pivots = self.client_medians[client.name]
                self.shareable[FOConstants.PIVOTS] = pivots
            else:
                self.random_select_flow(abort_signal, fl_ctx)

            self.median_size_collection_flow(abort_signal, fl_ctx)
            self.median_data_purge_flow(abort_signal, fl_ctx)
            self.controller.log_info(fl_ctx, f"task {self.task_name} control flow end.")
            task_flow_round += 1

    def random_select_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        """
            random select one server, and random select one value ( called it r-value) as median approximation
        """
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow random_select_flow started.")
        self.task_name = FOConstants.AGGR_MEDIAN_RANDOM_TASK

        clients = fl_ctx.get_engine().get_clients()
        import random

        random.shuffle(clients)
        task = Task(name=self.task_name, data=self.shareable, result_received_cb=self.task_results_cb)
        self.controller.send_and_wait(
            task=task,
            targets=clients[:1],
            fl_ctx=fl_ctx,
            abort_signal=abort_signal,
        )
        self.random_select_post_fn(fl_ctx)
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow random_select_flow end.")

    def random_select_post_fn(self, fl_ctx: FLContext):
        print(f"random_select_post_fn(), result={self.result}")

        for client_name in self.result:
            print(f"process Client {client_name}")
            stats = self.result[client_name][FeatureStatsConstants.STATS]
            if stats and FOConstants.PIVOTS in stats:
                r_values = stats[FOConstants.PIVOTS]
                self.shareable[FOConstants.PIVOTS] = r_values
            else:
                print(f"process Client {client_name} has NO stats result")

        print("on controller: r values = ", self.shareable[FOConstants.PIVOTS])

    def get_pivots(self) -> Union[Dict[str, float], None]:
        if FOConstants.PIVOTS in self.shareable:
            return self.shareable[FOConstants.PIVOTS]
        else:
            return None

    def median_size_collection_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        """
            send the random selected r (median approximation) to all servers
            and collect the size of elements that's greater than r (r-values)
            the returned size is called m (m-values)
        """
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow median_size_collection_flow started.")
        self.task_name = FOConstants.AGGR_MEDIAN_SIZE_COLL_TASK
        task = Task(name=self.task_name, data=self.shareable, result_received_cb=self.task_results_cb)
        clients = fl_ctx.get_engine().get_clients()

        self.controller.broadcast_and_wait(
            task=task,
            targets=None,
            min_responses=len(clients),
            fl_ctx=fl_ctx,
            wait_time_after_min_received=1,
            abort_signal=abort_signal,
        )
        self.median_size_collect_post_fn(fl_ctx)
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow median_size_collection_flow end.")

    def median_size_collect_post_fn(self, fl_ctx: FLContext):
        k_values = self.shareable[FOConstants.K_VALUES]
        m_values = {}
        l_values = {}
        e_values = {}

        self.shareable[FOConstants.MEDIAN_ACTION] = {}

        def set_value(col: str, x: {}, v: int):
            if col in x:
                x[feat_name] += v
            else:
                x[feat_name] = v

        print("median_size_collect_post_fn = result ", self.result)

        for client_name in self.result:
            stats = self.result[client_name][FeatureStatsConstants.STATS][FOConstants.PIVOT_SIZES]
            print(f"on controller side: client_name = {client_name}, m_values=", stats)
            for feat_name in stats:
                (m, e, l) = stats[feat_name]
                set_value(feat_name, m_values, m)
                set_value(feat_name, l_values, l)
                set_value(feat_name, e_values, e)

        print("m_values =", m_values)
        print("l_values =", l_values)
        print("e_values =", e_values)

        # stop check
        delta = {}
        pivot_sizes = {}
        for feat_name in e_values:
            pivot_sizes[feat_name] = (m_values[feat_name], e_values[feat_name], l_values[feat_name])

            if e_values[feat_name] >= abs(m_values[feat_name] - l_values[feat_name]):
                self.shareable[FOConstants.MEDIAN_ACTION].update(
                    {feat_name: FOConstants.STOP_ACTION}
                )
            else:
                m_ratio = m_values[feat_name] / (m_values[feat_name] + l_values[feat_name] + e_values[feat_name])
                l_ratio = l_values[feat_name] / (m_values[feat_name] + l_values[feat_name] + e_values[feat_name])
                if abs(m_ratio - 0.5) < 0.005 or abs(l_ratio - 0.5) < 0.005:
                    self.shareable[FOConstants.MEDIAN_ACTION].update(
                        {feat_name: FOConstants.STOP_ACTION}
                    )
                else:
                    delta[feat_name] = m_values[feat_name] + e_values[feat_name] - k_values[feat_name]
                    print("feature=", feat_name, "delta m-k =", delta[feat_name])
                    if delta[feat_name] < 0:
                        k_values[feat_name] = k_values[feat_name] - m_values[feat_name] - e_values[feat_name]
                        self.shareable[FOConstants.MEDIAN_ACTION].update(
                            {feat_name: FOConstants.DISCARD_GREATER_SET_ACTION}
                        )
                    elif delta[feat_name] > 0:
                        self.shareable[FOConstants.MEDIAN_ACTION].update(
                            {feat_name: FOConstants.DISCARD_LESS_SET_ACTION}
                        )
                    else:
                        self.shareable[FOConstants.MEDIAN_ACTION].update(
                            {feat_name: FOConstants.STOP_ACTION}
                        )

        self.shareable[FOConstants.K_VALUES] = k_values
        print("MEDIAN_ACTION =", self.shareable[FOConstants.MEDIAN_ACTION])
        self.shareable[FOConstants.PIVOT_SIZES] = pivot_sizes

    def median_data_purge_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow median_data_purge_flow started.")
        self.task_name = FOConstants.AGGR_MEDIAN_DATA_PURGE_TASK
        task = Task(name=self.task_name, data=Shareable(), result_received_cb=self.task_results_cb)
        clients = fl_ctx.get_engine().get_clients()

        self.controller.broadcast_and_wait(
            task=task,
            targets=None,
            min_responses=len(clients),
            fl_ctx=fl_ctx,
            wait_time_after_min_received=1,
            abort_signal=abort_signal,
        )
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow median_data_purge_flow end.")

    def stop_actions(self) -> bool:
        if FOConstants.MEDIAN_ACTION in self.shareable:
            feature_actions = self.shareable[FOConstants.MEDIAN_ACTION]
            greater_k_values = [
                feat
                for feat in feature_actions
                if feature_actions[feat] == FOConstants.DISCARD_GREATER_SET_ACTION
            ]
            if len(greater_k_values) > 0:
                return False
            else:
                lesser_k_values = [
                    feat
                    for feat in feature_actions
                    if feature_actions[feat] == FOConstants.DISCARD_LESS_SET_ACTION
                ]
                if len(lesser_k_values) > 0:
                    return False
                else:
                    return True
        else:
            return False


class AggrHistogramController(TaskController):
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

    def _aggregate_global_histogram(self, hist_type_key: str) -> Dict[Histogram]:
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


class FacetsOverviewController(Controller):
    def __int__(self):
        self.proto = None
        print("self.proto 1 = ", self.proto)

    def control_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        controller = self
        controller.proto = ProtoDatasetFeatureStatisticsList()
        client_stats_controller = ClientStatsController()
        client_stats_controller.set_controller(controller)
        client_stats_controller.set_proto(controller.proto)

        client_stats_controller.task_control_flow(abort_signal, fl_ctx)
        rc = client_stats_controller.get_return_code()
        if rc == ReturnCode.OK:

            aggr_means = client_stats_controller.get_aggr_means()
            aggr_counts = client_stats_controller.get_aggr_counts()
            client_medians = client_stats_controller.get_client_medians()

            shareable = Shareable()
            shareable[FOConstants.AGGR_MEANS] = aggr_means
            shareable[FOConstants.AGGR_COUNTS] = aggr_counts

            aggr_var_controller = AggregateVarController()
            aggr_var_controller.set_controller(controller)
            aggr_var_controller.set_sharable(shareable)
            aggr_var_controller.task_control_flow(abort_signal, fl_ctx)
            rc = aggr_var_controller.get_return_code()
            if rc == ReturnCode.OK:
                aggr_std_devs = aggr_var_controller.get_aggr_std_dev()
                # update std_devs for protos
                aggr_median_controller = AggregateMedianController()
                aggr_median_controller.set_controller(controller)

                aggr_median_controller.set_counts(aggr_counts)
                aggr_median_controller.set_client_medians(client_medians)
                rc = aggr_median_controller.get_return_code()
                if rc == ReturnCode.OK:
                    aggr_median_controller.shareable.update(shareable)
                    aggr_median_controller.task_control_flow(abort_signal, fl_ctx)

                    aggr_medians = aggr_median_controller.get_pivots()

                    total_count = client_stats_controller.get_total_count()
                    proto_ds = controller.proto.datasets.add(name="global", num_examples=total_count)
                    for src in controller.proto.datasets[0].features:
                        dest = proto_ds.features.add(type=src.type, name=src.name)
                        if src.num_stats:
                            dest.num_stats.std_dev = aggr_std_devs[src.name]
                            dest.num_stats.mean = aggr_means[src.name]
                            dest.num_stats.min = client_stats_controller.get_aggr_mins()[src.name]
                            dest.num_stats.max = client_stats_controller.get_aggr_maxs()[src.name]
                            dest.num_stats.median = aggr_medians[src.name]
                            dest.num_stats.num_zeros = client_stats_controller.get_aggr_zeros()[src.name]

                            self._populate_global_common_stats(dest.num_stats,
                                                               client_stats_controller.get_aggr_missings()[src.name],
                                                               aggr_counts[src.name])

                        elif src.string_stats:
                            common_stats = # TODO
                            dest.string_stats

                else:
                    logging.error(f"no result returned for {aggr_median_controller.task_name} ")

            else:
                logging.error(f"no result returned for {aggr_var_controller.task_name} ")

        else:
            logging.error(f"no result returned for {client_stats_controller.task_name} ")

    def start_controller(self, fl_ctx: FLContext):
        pass

    def stop_controller(self, fl_ctx: FLContext):
        pass

    def process_result_of_unknown_task(
            self, client: Client, task_name: str, client_task_id: str, result: Shareable, fl_ctx: FLContext
    ):
        pass

    def _populate_global_common_stats(self, num_stats, missings, count):
        common_stats = num_stats.common_stats
        common_stats.num_missing = missings
        common_stats.num_non_missing = count
        common_stats.min_num_values = num_stats.min
        common_stats.max_num_values = num_stats.max
        common_stats.avg_num_values = num_stats.mean
