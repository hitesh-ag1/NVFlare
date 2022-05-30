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

import glob
import logging
import os
import pandas as pd

from nvflare.apis.dxo import DXO, DataKind
from nvflare.apis.executor import Executor
from nvflare.apis.fl_constant import ReservedKey, ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.shareable import Shareable, make_reply
from nvflare.apis.signal import Signal
from facets_overview.generic_feature_statistics_generator import GenericFeatureStatisticsGenerator
import base64
import pandas as pd


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
                dxo = DXO(data_kind=DataKind.METRICS, data=result)
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

    def _gen_stats(self, named_dfs: list) -> str:
        proto = self.gfsg.ProtoFromDataFrames(named_dfs)
        return base64.b64encode(proto.SerializeToString()).decode("utf-8")

    def load_data(self, client_name, fl_ctx: FLContext):
        self.log_info(fl_ctx, f"load data for client {client_name}")

        features = ["Age", "Workclass", "fnlwgt", "Education", "Education-Num", "Marital Status",
                    "Occupation", "Relationship", "Race", "Sex", "Capital Gain", "Capital Loss",
                    "Hours per week", "Country", "Target"]

        self.log_info(fl_ctx, f"loading training data for client {client_name}")
        train_data = pd.read_csv(
            "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data",
            names=features,
            sep=r'\s*,\s*',
            engine='python',
            na_values="?")

        self.log_info(fl_ctx, f"loading test data for client {client_name}")
        test_data = pd.read_csv(
            "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.test",
            names=features,
            sep=r'\s*,\s*',
            skiprows=[0],
            engine='python',
            na_values="?")

        data = [{'name': 'train', 'table': train_data},
                {'name': 'test', 'table': test_data}]

        self.log_info(fl_ctx, f"load data done for client {client_name}")
        return data

    def client_exec(self, task_name: str, shareable: Shareable, fl_ctx: FLContext, abort_signal: Signal) -> dict:
        client_name = fl_ctx.get_prop(ReservedKey.CLIENT_NAME)
        self.log_info(fl_ctx, f"exec {task_name} for client {client_name}")
        return {"result": f"{self._gen_stats(self.data)}"}

