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
from typing import Optional

from nvflare.app_common.executors.statistics.base_statistics_executor import BaseStatsExecutor
from nvflare.app_common.app_constant import StatisticsConstants as StatsConstant


class StdHistogramExecutor(BaseStatsExecutor, ABC):
    def __init__(
            self,
            bins: int,
            global_bin_range: Optional[(float, float)] = None,
            task_name: str = StatsConstant.STD_HIST_TASK,
    ):
        """
        :param bins: numbers of buckets or bins needed for the histogram
        :param global_bin_range: global bin's value range tuple. If specified, the bins will be created according to
               the range specified. If not specified, the range will be try to dynamically calculated.
        :param task_name: name of task default to "stats_std_histogram"
        """
        super().__init__(task_name)
        self.bins = bins
        self.global_bin_range = global_bin_range

    def set_bins(self, bins):
        self.bins = bins

    def set_global_bin_range(self, bin_range:(float, float)):
        self.global_bin_range = bin_range
