# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
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

from abc import ABC

from nvflare.apis.dxo import DXO, DataKind
from nvflare.apis.executor import Executor
from nvflare.apis.fl_constant import ReservedKey, ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.shareable import Shareable, make_reply
from nvflare.apis.signal import Signal
from nvflare.app_common.executors.statistics.base_statistics_executor import BaseStatsExecutor
from pandas import DataFrame


class DataframeBaseStatsExecutor(BaseStatsExecutor, ABC):
    """
       DataframeBaseStatsExecutor handles Dataframe datasets

    """

    def __init__(self, task_name):
        super().__init__()
        self.data = None
        self.task_name = task_name

    def load_data(self, task_name: str, client_name: str, fl_ctx: FLContext) -> DataFrame:
        pass
