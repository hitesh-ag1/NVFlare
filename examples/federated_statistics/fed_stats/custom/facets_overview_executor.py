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

import base64
import glob
import logging
import os
from typing import Dict, List
import pandas as pd
from facets_overview.generic_feature_statistics_generator import GenericFeatureStatisticsGenerator
from facets_overview.feature_statistics_pb2 import (
    DatasetFeatureStatisticsList,
    DatasetFeatureStatistics,
    FeatureNameStatistics,
    CustomStatistic,
    NumericStatistics,
    StringStatistics,
    CommonStatistics,
    Histogram,
    RankHistogram,
)
from feature_stats.feature_stats_def import (
    DatasetStatisticsList,
)
from feature_stats.feature_statistics_generator import (
    FeatureStatsGenerator,
    DataType,
)

from pyhocon import ConfigFactory

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
        self.log_info(fl_ctx, f"Executing {task_name}")
        try:
            client_name = fl_ctx.get_prop(ReservedKey.CLIENT_NAME)
            self.data = self.load_data(client_name, fl_ctx)
            if not self.data:
                self.log_error(fl_ctx, f"Load data for client {client_name} failed!")
                return make_reply(ReturnCode.ERROR)
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

    def load_data(self, client_name: str, fl_ctx: FLContext) -> object:
        pass

    def client_exec(self, task_name: str, shareable: Shareable, fl_ctx: FLContext, abort_signal: Signal) -> Shareable:
        pass


class FacetsOverviewExecutor(BaseAnalyticsExecutor):
    def __init__(self):
        super().__init__()
        self.gfsg = GenericFeatureStatisticsGenerator()
        self.gen = FeatureStatsGenerator()

    def load_data(self, client_name, fl_ctx: FLContext):
        self.log_info(fl_ctx, f"load data for client {client_name}")

        workspace_dir, run_dir, config_path = self._get_app_paths(client_name, fl_ctx)
        config = self._load_config(config_path)

        features = config[f"fed_stats.data.features"]
        data_path = self._get_data_path(workspace_dir, client_name, config)
        skiprows = config[f"fed_stats.data.clients.{client_name}.skiprows"]

        train_data = pd.read_csv(
            data_path, names=features, sep=r"\s*,\s*", skiprows=skiprows, engine="python", na_values="?"
        )
        print(train_data.head())
        # for my implementation
        data = {client_name: train_data}
        # for google facets-overview
        # data = [{"name": f"{client_name}", "table": train_data}]
        self.log_info(fl_ctx, f"load data done for client {client_name}")
        return data

    def client_exec(self, task_name: str, shareable: Shareable, fl_ctx: FLContext, abort_signal: Signal) -> dict:
        client_name = fl_ctx.get_prop(ReservedKey.CLIENT_NAME)
        self.log_info(fl_ctx, f"exec {task_name} for client {client_name}")
        return {"encoded_stats": self._gen_stats(self.data)}

    # Utility methods
    #########################################################

    def _load_config(self, config_path: str):
        return ConfigFactory.parse_file(config_path)

    def _gen_stats(self, named_dfs: Dict[str, pd.DataFrame]) -> object:
        stats: DatasetStatisticsList = self.gen.generate_statistics(named_dfs)
        # stats = self.gfsg.ProtoFromDataFrames(named_dfs)
        import pickle, base64
        data = base64.encodebytes(pickle.dumps(stats))
        return data

    def _get_app_paths(self, client_name, fl_ctx: FLContext) -> (str, str, str):
        workspace = fl_ctx.get_prop(FLContextKey.WORKSPACE_OBJECT)
        workspace_dir = workspace.get_root_dir()
        run_dir = fl_ctx.get_engine().get_workspace().get_app_dir(fl_ctx.get_run_number())
        config_path = f"{run_dir}/config/application.conf"
        return workspace_dir, run_dir, config_path

    def _get_data_path(self, workspace_dir, client_name, config) -> str:
        data_file_name = config[f"fed_stats.data.clients.{client_name}.filename"]
        return f"{workspace_dir}/{data_file_name}"
