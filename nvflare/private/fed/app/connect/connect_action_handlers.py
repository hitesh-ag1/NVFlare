import time
from typing import Callable, Dict, List, Optional

from nvflare.apis.client import Client
from nvflare.apis.dxo import from_shareable
from nvflare.apis.fl_constant import ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.broadcast import Broadcast
from nvflare.apis.impl.controller import ClientTask, Controller, Task
from nvflare.apis.impl.operator import Operator
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal
from nvflare.app_common.abstract.statistics_spec import Bin, Histogram, StatisticConfig
from nvflare.app_common.abstract.statistics_writer import StatisticsWriter
from nvflare.app_common.app_constant import StatisticsConstants as StC
from nvflare.app_common.statistics.numeric_stats import get_global_stats
from nvflare.app_common.statistics.statisitcs_objects_decomposer import fobs_registration
from nvflare.fuel.utils import fobs
from .messaage import create_message, unpack_message
from nvflare.private.fed.server.fed_server import FederatedServer


def broadcast_handler(parameters: dict, request, fed_server: FederatedServer):
    print(parameters)

    broadcast_op = Broadcast(fed_server.fl_ctx)
    client_task = broadcast_op.op(parameters, result_received_cb)

    client_name = client_task.client.name
    task_name = client_task.task.name
    client_task_results = {
        "client": client_name,
        "task": task_name,
        "result": client_task.result
    }
    result = client_task.result
    response_in_bytes = create_message(client_task_results, "text/json", "utf-8")
    client_task.result = None
    request.sendall(response_in_bytes)


def result_received_cb(client_task: ClientTask, fl_ctx: FLContext):
    print(f"Processing {client_task.task.name} result_received_cb from client { client_task.client.name}")
    return client_task
