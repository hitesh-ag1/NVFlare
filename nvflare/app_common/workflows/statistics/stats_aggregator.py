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

from nvflare.apis.client import Client
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.controller import Controller
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal


class StatisticsAggregator(Controller):

    def __int__(self,
                global_bin_range_min,
                global_bin_range_max,
                dynamic_bin_range=False,
                global_bins=20,
                ):
        self.global_bin_range_min = global_bin_range_min
        self.global_bin_range_max = global_bin_range_max
        self.global_bins = global_bins
        self.dynamic_bin_range = dynamic_bin_range

    @property
    def task_name(self):
        return "fed_stats"

    def stop_controller(self, fl_ctx: FLContext):
        pass

    def process_result_of_unknown_task(self, client: Client, task_name: str, client_task_id: str, result: Shareable,
                                       fl_ctx: FLContext):
        pass

    def start_controller(self, fl_ctx: FLContext):
        pass

    def control_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        pass

    def _get_result(self, fl_ctx: FLContext):
        """
        get after the calculation
        """
        pass
