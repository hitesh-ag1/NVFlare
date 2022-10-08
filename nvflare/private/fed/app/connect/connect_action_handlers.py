import time
from typing import Callable, Dict, List, Optional

from nvflare.apis.client import Client
from nvflare.apis.dxo import from_shareable
from nvflare.apis.fl_constant import ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.controller import ClientTask, Controller, Task
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal
from nvflare.app_common.abstract.statistics_spec import Bin, Histogram, StatisticConfig
from nvflare.app_common.abstract.statistics_writer import StatisticsWriter
from nvflare.app_common.app_constant import StatisticsConstants as StC
from nvflare.app_common.statistics.numeric_stats import get_global_stats
from nvflare.app_common.statistics.statisitcs_objects_decomposer import fobs_registration
from nvflare.fuel.utils import fobs


def broadcast_handler(self, parameters: dict, request):

    print(parameters)

    task_props = {StC.STATISTICS_TASK_KEY: StC.STATS_1st_STATISTICS}
    task = Task(name=self.task_name, data=parameters, result_received_cb=self.results_cb_fn, props=task_props)

    self.broadcast_and_wait(
        task=task,
        targets=None,
        min_responses=self.min_clients,
        fl_ctx=fl_ctx,
        wait_time_after_min_received=1,
     )

    def results_cb_fn():

        request.sendall(b"broadcast parameters")
