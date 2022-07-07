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

from df_executors import MyDFCountExecutor, MyDFMeanExecutor, MyDFVarExecutor, MyDFStdHistExecutor, MyDFQuanHistExecutor
from nvflare.apis.fl_context import FLContext
from nvflare.app_common.app_constant import StatisticsConstants as StatsConstant
from nvflare.app_common.executors.statistics.stats_executor import StatsExecutor


class MyDFStatsExecutor(StatsExecutor):
    def __init__(
            self,
            executors=None,
            task_name: str = StatsConstant.BASIC_STATS_TASK,
    ):
        super().__init__()
        if executors is None:
            executors = {
                StatsConstant.MEAN_TASK: MyDFMeanExecutor(),
                StatsConstant.COUNT_TASK: MyDFCountExecutor(),
                StatsConstant.VAR_TASK: MyDFVarExecutor(),
                StatsConstant.QUAN_HIST_TASK: MyDFQuanHistExecutor(),
                StatsConstant.STD_HIST_TASK: MyDFStdHistExecutor()
            }
        self.task_name = task_name
        self.executors = executors

    def load_data(self, task_name: str, client_name, fl_ctx: FLContext):
        pass
