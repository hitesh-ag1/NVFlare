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

from typing import Dict

import pandas as pd
from facets_overview.feature_statistics_pb2 import (
    Histogram
)
from pyhocon import ConfigFactory

from facets_overview_constants import FOConstants
from feature_stats.feature_entry import FeatureEntryGenerator
from feature_stats.feature_statistics_generator import FeatureStatsGenerator
from feature_stats.feature_stats_constants import FeatureStatsConstants
from feature_stats.feature_stats_def import (
    DatasetStatisticsList,
    DataType,
    Histogram,
    HistogramType,
    BucketRange,
)
from nvflare.apis.dxo import DXO, DataKind
from nvflare.apis.executor import Executor
from nvflare.apis.fl_constant import FLContextKey, ReservedKey, ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.shareable import Shareable, make_reply
from nvflare.apis.signal import Signal


class BaseAnalyticsExecutor(Executor):
    def __init__(self):
        super().__init__()
        self.data = None

    def execute(self, task_name: str, shareable: Shareable, fl_ctx: FLContext, abort_signal: Signal) -> Shareable:
        client_name = fl_ctx.get_prop(ReservedKey.CLIENT_NAME)
        self.log_info(fl_ctx, f"Executing task '{task_name}' for client: '{client_name}'")
        try:
            result = self.client_exec(task_name, shareable, fl_ctx, abort_signal)
            if abort_signal.triggered:
                return make_reply(ReturnCode.TASK_ABORTED)
            if result:
                dxo = DXO(data_kind=DataKind.ANALYTIC, data=result)
                return dxo.to_shareable()
            else:
                return make_reply(ReturnCode.EXECUTION_EXCEPTION)

        except BaseException as e:
            self.log_exception(fl_ctx, f"Task {task_name} failed. Exception: {e.__str__()}")
            return make_reply(ReturnCode.EXECUTION_EXCEPTION)

    def load_data(self, task_name: str, client_name: str, fl_ctx: FLContext) -> object:
        pass

    def client_exec(self, task_name: str, shareable: Shareable, fl_ctx: FLContext, abort_signal: Signal) -> Shareable:
        pass


class FacetsOverviewExecutor(BaseAnalyticsExecutor):
    def __init__(self):
        super().__init__()
        self.gen = FeatureStatsGenerator()
        self.result = dict()
        self.client_stats_task = FOConstants.CLIENT_STATS_TASK
        self.aggr_var_task = FOConstants.AGGR_VAR_TASK
        self.data = {}
        self.origin_data = {}
        self.greater_than = {}
        self.less_than = {}
        self.equals_to = {}
        self.hist_bins = 10

    def load_data(self, task_name: str, client_name, fl_ctx: FLContext) -> Dict[str, pd.DataFrame]:
        if task_name == self.client_stats_task:
            self.log_info(fl_ctx, f"load data for client {client_name}")
            try:
                workspace_dir, run_dir, config_path = self._get_app_paths(client_name, fl_ctx)
                config = self._load_config(config_path)

                features = config["fed_stats.data.features"]
                data_path = self._get_data_path(workspace_dir, client_name, config)
                skiprows = config[f"fed_stats.data.clients.{client_name}.skiprows"]

                train_data = pd.read_csv(
                    data_path, names=features, sep=r"\s*,\s*", skiprows=skiprows, engine="python", na_values="?"
                )
                import numpy as np
                print(train_data.head())
                print(train_data.info())
                data = {client_name: train_data}
                self.log_info(fl_ctx, f"load data done for client {client_name}")
                return data

            except BaseException as e:
                raise Exception(f"Load data in task: {task_name} for client {client_name} failed! {e}")
        else:
            pass

    def client_exec(self, task_name: str, shareable: Shareable, fl_ctx: FLContext, abort_signal: Signal) -> dict:
        client_name = fl_ctx.get_prop(ReservedKey.CLIENT_NAME)
        self.log_info(fl_ctx, f"exec {task_name} for client {client_name}")

        if task_name == self.client_stats_task:

            named_df: Dict[str, pd.DataFrame] = self.load_data(task_name, client_name, fl_ctx)
            self.data = named_df
            self.origin_data = named_df
            bins = self._get_std_histogram_bins(shareable)

            return {FeatureStatsConstants.STATS: self._gen_stats(named_df, bins)}

        elif task_name == self.aggr_var_task:
            variances = self._calc_variance(client_name, shareable)
            # perform calculation for global aggregation
            self.log_info(fl_ctx, f"exec {task_name} for client {client_name}")
            aggr_vars = {FOConstants.AGGR_VARS: variances}
            self.log_info(fl_ctx, f"aggr_vars= {aggr_vars}")
            return {FeatureStatsConstants.STATS: self._encode_data(aggr_vars)}

        elif task_name == FOConstants.AGGR_MEDIAN_RANDOM_TASK:
            self.log_info(fl_ctx, f"exec {task_name} for client {client_name}")
            median_actions = {}
            if FOConstants.MEDIAN_ACTION in shareable:
                median_actions = shareable[FOConstants.MEDIAN_ACTION]
            old_pivots = {}
            if FOConstants.PIVOTS in shareable:
                old_pivots = shareable[FOConstants.PIVOTS]

            df = self.data[client_name]
            pivots = {}
            for col in df:
                if col not in median_actions or median_actions[col] != FOConstants.STOP_ACTION:
                    pivots[col] = df[df[col].notnull()][col].sample().values[0]
                else:
                    pivots[col] = old_pivots[col]

            return {FeatureStatsConstants.STATS: self._encode_data({FOConstants.PIVOTS: pivots})}

        elif task_name == FOConstants.AGGR_MEDIAN_SIZE_COLL_TASK:
            self.log_info(fl_ctx, f"exec {task_name} for client {client_name}")
            pivots: Dict[str, float] = shareable[FOConstants.PIVOTS]
            pivot_sizes = {}

            df = self.data[client_name]
            greater_than_df = pd.DataFrame()
            less_than_df = pd.DataFrame()
            equal_to_df = pd.DataFrame()

            for col in df:
                data_type = FeatureEntryGenerator.dtype_to_data_type(df[col].dtype)

                if data_type == DataType.INT or data_type == DataType.FLOAT:
                    greater_than_df = df[df[col] > pivots[col]]
                    less_than_df = df[df[col] < pivots[col]]
                    equal_to_df = df[df[col] == pivots[col]]
                    pivot_sizes[col] = (greater_than_df[col].size, equal_to_df[col].size, less_than_df[col].size)
                # todo:
                # elif data_type == DataType.DATETIME:
                #     FeatureEntryGenerator.dt_to_num_converter(df[col])

            self.greater_than = {client_name: greater_than_df}
            self.less_than = {client_name: less_than_df}
            self.equals_to = {client_name: equal_to_df}

            self.log_info(fl_ctx, f"exec {task_name} for client {client_name}")
            return {FeatureStatsConstants.STATS: self._encode_data({FOConstants.PIVOT_SIZES: pivot_sizes})}

        elif task_name == FOConstants.AGGR_MEDIAN_DATA_PURGE_TASK:
            self.log_info(fl_ctx, f"exec {task_name} for client {client_name}")
            action = FOConstants.CONTINUE_ACTION
            if FOConstants.MEDIAN_ACTION in shareable:
                feature_actions = shareable[FOConstants.MEDIAN_ACTION]
                if feature_actions == FOConstants.DISCARD_LESS_SET_ACTION:
                    self.data = self.greater_than
                    self.less_than = {}
                elif feature_actions == FOConstants.DISCARD_GREATER_SET_ACTION:
                    self.data = self.less_than
                    self.greater_than = {}
                else:
                    action = FOConstants.STOP_ACTION
            else:
                action = FOConstants.STOP_ACTION
            return {FeatureStatsConstants.STATS: self._encode_data({FOConstants.MEDIAN_ACTION: action})}

        elif task_name == FOConstants.AGGR_HISTOGRAM_TASK:

            self.log_info(fl_ctx, f"exec {task_name} for client {client_name}")
            # max and min must available for standard histogram
            # otherwise we should fail the calculation
            bins = self._get_std_histogram_bins(shareable)
            feature_ranges = self._get_num_feature_range(shareable)
            std_histograms = {}
            quantile_histograms = {}
            df = self.origin_data[client_name]
            for feat_name in feature_ranges:
                data_type = FeatureEntryGenerator.dtype_to_data_type(df[feat_name].dtype)
                if data_type == DataType.INT or data_type == DataType.FLOAT:
                    std_histo: Histogram = self.gen.get_histogram(df[feat_name].values,
                                                                  num_buckets=bins,
                                                                  histogram_type=HistogramType.STANDARD,
                                                                  bucket_range=feature_ranges[feat_name])

                    quan_histo: Histogram = self.gen.get_histogram(df[feat_name].values,
                                                                   num_buckets=bins,
                                                                   histogram_type=HistogramType.QUANTILES)
                    std_histograms[feat_name] = std_histo
                    quantile_histograms[feat_name] = quan_histo
                else:
                    # todo:
                    pass

            return {FeatureStatsConstants.STATS: self._encode_data({
                HistogramType.STANDARD: std_histograms,
                HistogramType.QUANTILES: quantile_histograms,
            })}
        else:
            # Task execution error, return EXECUTION_EXCEPTION Shareable
            self.log_exception(fl_ctx, f"unknown task name: {task_name}")
            return make_reply(ReturnCode.TASK_UNKNOWN)

    # Utility methods
    #########################################################
    def _get_std_histogram_bins(self, shareable: Shareable) -> int:
        if FOConstants.BINS in shareable:
            bins = shareable[FOConstants.BINS]
        else:
            bins = self.hist_bins
        return bins

    def _get_num_feature_range(self, shareable: Shareable) -> Dict[str, BucketRange]:
        maxes = shareable[FOConstants.AGGR_MAXES]
        mins = shareable[FOConstants.AGGR_MINS]
        feature_ranges = {}
        for feat_name in maxes:
            min_value = mins[feat_name]
            max_value = maxes[feat_name]
            feature_ranges[feat_name] = BucketRange(min_value, max_value)
        return feature_ranges

    def _calc_variance(self, client_name: str, shareable: Shareable) -> Dict[str, float]:
        means: Dict[str, float] = shareable[FOConstants.AGGR_MEANS]
        counts: Dict[str, float] = shareable[FOConstants.AGGR_COUNTS]
        df = self.data[client_name]
        variances = {}
        for feat in means:
            tmp = (df[feat] - means[feat]) * (df[feat] - means[feat]) / (counts[feat] - 1)
            variances[feat] = tmp.sum()
        return variances

    def _load_config(self, config_path: str):
        return ConfigFactory.parse_file(config_path)

    def _encode_data(self, data):
        import base64
        import pickle

        data = base64.encodebytes(pickle.dumps(data))
        return data

    def _gen_stats(self, named_dfs: Dict[str, pd.DataFrame], hist_bins: int = 10) -> object:
        stats: DatasetStatisticsList = self.gen.generate_statistics(dfs=named_dfs, hist_bins=hist_bins)
        return self._encode_data(stats)

    def _aggreg_stats(self, task_name: str) -> object:
        stats: DatasetStatisticsList = self.result[self.client_stats_task]
        if not stats:
            raise ValueError("individual clients' stats are not available")
        aggr_stats = stats
        return self._encode_data(aggr_stats)

    def _get_app_paths(self, client_name, fl_ctx: FLContext) -> (str, str, str):
        workspace = fl_ctx.get_prop(FLContextKey.WORKSPACE_OBJECT)
        workspace_dir = workspace.get_root_dir()
        job_dir = fl_ctx.get_engine().get_workspace().get_app_dir(fl_ctx.get_job_id())
        config_path = f"{job_dir}/config/application.conf"
        return workspace_dir, job_dir, config_path

    def _get_data_path(self, workspace_dir, client_name, config) -> str:
        data_file_name = config[f"fed_stats.data.clients.{client_name}.filename"]
        return f"{workspace_dir}/{data_file_name}"
