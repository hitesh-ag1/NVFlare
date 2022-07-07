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

from nvflare.app_common.app_constant import StatisticsConstants as StatsConstant
from nvflare.app_common.executors.statistics.count_executor import CountExecutor


class DataFrameCountExecutor(CountExecutor):
    def __init__(
            self,
            task_name: str = StatsConstant.COUNT_TASK,
    ):
        super().__init__(task_name)

    def client_exec(self, task_name: str, shareable: Shareable, fl_ctx: FLContext, abort_signal: Signal) -> Shareable:
        result = Shareable()
        result["local_count"] = self._get_count()
        return result

    def _get_count(self):
        result = {}
        df = DataFrame(self.data)
        for feature_name in df:
            result[feature_name]= df[feature_name].count

        return result


