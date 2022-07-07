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

from nvflare.app_common.executors.statistics.base_statistics_executor import BaseStatsExecutor
from nvflare.app_common.app_constant import StatisticsConstants as StatsConstant


class QuantileHistogramExecutor(BaseStatsExecutor, ABC):
    def __init__(
            self,
            bins: int,
            task_name: str = StatsConstant.QUAN_HIST_TASK,
    ):
        """
        :param bins: numbers of buckets or bins needed for the histogram
        :param task_name: name of task default to "stats_quantile_histogram"
        """
        super().__init__()
        self.bins = bins
        self.task_name = task_name

    def set_bins(self, bins):
        self.bins = bins
