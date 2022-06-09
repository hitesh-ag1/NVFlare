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
from abc import ABC

from nvflare.apis.client import Client
from nvflare.apis.dxo import from_shareable
from nvflare.apis.fl_constant import FLContextKey, ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.controller import ClientTask, Controller, Task
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal
from feature_stats.proto_stats_utils import (
    _add_client_stats_to_proto,
)
from feature_stats.feature_stats_def import (
    BasicNumStats,
    Bucket,
    CommonStatistics,
    DatasetStatistics,
    DatasetStatisticsList,
    FeatureStatistics,
    FreqAndValue,
    Histogram,
    HistogramType,
    NumericStatistics,
    RankBucket,
    RankHistogram,
    StringStatistics,
    DataType
)
from feature_stats import feature_statistics_pb2 as fs

from feature_stats.feature_statistics_pb2 import (
    DatasetFeatureStatisticsList as ProtoDatasetFeatureStatisticsList,
    DatasetFeatureStatistics as ProtoDatasetFeatureStatistics,
    FeatureNameStatistics as ProtoFeatureNameStatistics,
    CustomStatistic as ProtoCustomStatistic,
    NumericStatistics as ProtoNumericStatistics,
    StringStatistics as ProtoStringStatistics,
    CommonStatistics as ProtoCommonStatistics,
    Histogram as ProtoHistogram,
    RankHistogram as ProtoRankHistogram,

)
from typing import Optional


class BaseAnalyticsController(Controller, ABC):
    def __init__(self, min_clients: int, task_name: str):
        """Base Controller for federated Analysis.
        Args:
            min_clients: how many client's statistics to gather before computing the global statistics.
            task_name: task name
        """
        super().__init__()
        self._min_clients = min_clients
        self._wait_time_after_min_received = 5
        self.run_dir = None
        self.task_name = task_name
        self.analytics_data = dict()
        self._results_cb = self.results_cb
        self._post_fn = self.post_fn

    def results_cb(self, client_task: ClientTask, fl_ctx: FLContext):
        client_task_name = client_task.task.name
        task_name = self.task_name
        client_name = client_task.client.name

        self.log_info(fl_ctx, f"Processing {task_name} result from client {client_name}")

        result = client_task.result
        rc = result.get_return_code()
        if rc == ReturnCode.OK:
            dxo = from_shareable(result)
            data_stats_dict = dxo.data
            data_kind = dxo.data_kind
            self.log_info(fl_ctx, f"Received result entries {data_stats_dict.keys()}, kind = ${data_kind}")
            self.analytics_data.update({client_name: data_stats_dict})
        else:
            self.log_error(
                fl_ctx, f"Ignore the client  {client_name} result. {task_name} tasked returned error code: {rc}"
            )

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

    def process_result_of_unknown_task(
            self, client: Client, task_name: str, client_task_id: str, result: Shareable, fl_ctx: FLContext
    ):
        self.log_warning(fl_ctx, f"Unknown task: {task_name} from client {client.name}.")


class FacetsOverviewController(BaseAnalyticsController):
    def __init__(self, min_clients: int = 1, task_name="facets_overview"):
        """Controller for federated facets Overview
        Args:
            min_clients: how many statistics to gather before computing the global statisitcs.
        """
        super().__init__(min_clients, task_name=task_name)
        self.proto = ProtoDatasetFeatureStatisticsList()

    def results_cb(self, client_task: ClientTask, fl_ctx: FLContext):
        super().results_cb(client_task, fl_ctx)
        import pickle, base64
        for client_name in self.analytics_data:
            encoded_stats = self.analytics_data[client_name]['encoded_stats']
            stats: DatasetStatisticsList = pickle.loads(base64.decodebytes(encoded_stats))
            self.analytics_data[client_name]['stats'] = stats

    def post_fn(self, fl_ctx: FLContext):
        logging.info("inside post function, save result to file ")
        proto_stats = self.proto

        for client_name in self.analytics_data:
            print(f"client  = {client_name}")
            _add_client_stats_to_proto(client_name, proto_stats, self.analytics_data)

        self.save_result_to_file(fl_ctx)

    def save_result_to_file(self, fl_ctx: FLContext, file_path: Optional[str] = None):
        import os
        import base64
        from pathlib import Path
        try:
            workspace = fl_ctx.get_prop(FLContextKey.WORKSPACE_OBJECT)
            workspace_dir = workspace.get_root_dir()
            base_dir = os.path.join(workspace_dir, f"{self.task_name}")
            if not file_path:
                result_path = os.path.join(base_dir, "demo.pb")
            else:
                result_path = os.path.join(base_dir, file_path)

            print("base dir = ", base_dir)
            print("task name = ", self.task_name)

            os.makedirs(Path(result_path).parent.absolute(), exist_ok=True)  # check permissions/handle failures
            logging.info(f"saving to {result_path}")
            data = base64.b64encode(self.proto.SerializeToString()).decode("utf-8")
            with open(result_path, "w") as text_file:
                text_file.write(data)
        except BaseException as e:
            logging.error(f"failed to save file {e}", exc_info=True)
            raise e

        # proto_global = proto_stats.datasets.add(name="global", num_examples=0)
        # proto_global.num_examples += ds.num_examples
        # feat_global = None
        # if len(proto_global.features) == 0:
        #     feat_global = proto_global.features.add(type=proto_data_type, name=f.name)
        #
        # for i in range(len(proto_global.features)):
        #     if proto_global.features[i].name == f.name:
        #         feat_global = proto_global.features[i]
        #     else:
        #         feat_global = proto_global.features.add(type=proto_data_type, name=f.name)
