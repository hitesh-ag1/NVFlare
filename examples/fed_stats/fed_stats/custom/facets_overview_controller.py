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
import logging
import os

from nvflare.apis.client import Client
from nvflare.apis.dxo import from_shareable
from nvflare.apis.fl_constant import FLContextKey, ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.controller import ClientTask, Controller, Task
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal
from abc import ABC


class BaseAnalyticsController(Controller, ABC):
    def __init__(self, min_clients: int, task_name: str):
        """Base Controller for federated Analysis.
        Args:
            min_clients: how many client's statistics to gather before computing the global statistics.
            task_name: task name
        """
        super().__init__()
        self._min_clients = min_clients
        self._wait_time_after_min_received = 1
        self.run_dir = None
        self.task_name = task_name
        self.analytics_data = dict()
        self._results_cb = self.results_cb
        self._post_fn = self.post_fn

    def results_cb(self, client_task: ClientTask, fl_ctx: FLContext):
        client_task_name = client_task.task.name
        task_name = self.task_name
        print("task_name = ", task_name)
        print("client_task_name =", client_task_name)

        client_name = client_task.client.name
        self.log_info(fl_ctx, f"Processing {task_name} result from client {client_name}")
        logging.info(f"Processing {task_name} result from client {client_name}")

        result = client_task.result
        rc = result.get_return_code()
        if rc == ReturnCode.OK:
            dxo = from_shareable(result)
            data_stat_dict = dxo.data
            self.log_info(fl_ctx, f"Received result entries {data_stat_dict.keys()}")
            self.analytics_data.update({client_name: data_stat_dict})
            for key in data_stat_dict.keys():
                self.log_info(fl_ctx, f"Client {client_name} finished {task_name} returned ${key}.")
        else:
            self.log_error(fl_ctx, f"Ignore the client  {client_name} result. {task_name} tasked returned error code: {rc}")

        # Cleanup task result
        client_task.result = None

    def post_fn(self, fl_ctx: FLContext):

        logging.info("I am here in base class")

        pass

    def control_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        self.log_info(fl_ctx, "control flow started.")
        if abort_signal.triggered:
            return
        task = Task(name=self.task_name, data=Shareable(), result_received_cb=self.results_cb)
        self.broadcast_and_wait(
            task=task,
            min_responses=self._min_clients,
            fl_ctx=fl_ctx,
            wait_time_after_min_received=self._wait_time_after_min_received,
            abort_signal=abort_signal,
        )

        if abort_signal.triggered:
            return

        logging.info("post function ")

        self.post_fn(fl_ctx)

        self.log_info(fl_ctx, "Analysis control flow finished.")

    def start_controller(self, fl_ctx: FLContext):
        self.run_dir = os.path.join(fl_ctx.get_prop(FLContextKey.APP_ROOT), "../..")

    def stop_controller(self, fl_ctx: FLContext):
        pass

    def process_result_of_unknown_task(self, client: Client, task_name: str, client_task_id: str, result: Shareable,
                                       fl_ctx: FLContext):
        self.log_warning(fl_ctx, f"Unknown task: {task_name} from client {client.name}.")


class FacetsOverviewController(BaseAnalyticsController):

    def __init__(self, min_clients: int = 1, task_name="facets_overview"):
        """Controller for federated facets Overview
        Args:
            min_clients: how many statistics to gather before computing the global statisitcs.
        """
        super().__init__(min_clients, task_name=task_name)

    def post_fn(self, fl_ctx: FLContext):
        logging.info("inside post function, save result to file ")

        for client_name in self.analytics_data:
            print(f"client  = {client_name}")
            result = self.analytics_data[client_name]
            if result:
                import os
                path = os.path.join(f"/tmp/nvflare/", f"{self.task_name}/{client_name}")
                os.makedirs(path, exist_ok=True) # check permissions/handle failures
                result_file = f"/tmp/nvflare/{self.task_name}/{client_name}/demo.pb"
                logging.info(f"saving to {result_file}")
                with open(result_file, "w") as text_file:
                    data = result["result"]
                    text_file.write(data)
            else:
                self.log_error(fl_ctx, f"no result returned for client {client_name} ")
