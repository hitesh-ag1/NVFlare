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
from typing import Dict, Union

from facets_overview_constants import FOConstants
from feature_stats.feature_stats_constants import FeatureStatsConstants
from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.controller import Task
from nvflare.apis.shareable import Shareable
from nvflare.apis.signal import Signal
from task_controller import TaskController


class GlobalMedianController(TaskController):
    def __init__(self):
        super().__init__()
        self.feature_counts = {}
        self.client_medians = {}
        self.task_name = FOConstants.AGGR_MEDIAN_TASK

    def set_counts(self, counts: Dict[str, int]):
        self.feature_counts = counts

    def set_client_medians(self, client_medians: dict):
        self.client_medians = client_medians

    def set_k_values(self):
        k_values = {}
        for feat in self.feature_counts:
            k_values[feat] = self.feature_counts[feat] / 2

        self.shareable[FOConstants.K_VALUES] = k_values

    def task_control_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow started.")
        if abort_signal.triggered:
            return
        task_flow_round = 1
        self.set_k_values()
        while not self.stop_actions() and task_flow_round < 2:
            self.controller.log_info(fl_ctx, f"task {self.task_name} k_values = {self.shareable[FOConstants.K_VALUES]}.")
            if FOConstants.PIVOT_SIZES in self.shareable:
                for feat_name in self.shareable[FOConstants.K_VALUES]:
                    m, e, l = self.shareable[FOConstants.PIVOT_SIZES][feat_name]
            else:
                self.controller.log_info(fl_ctx,f"task {self.task_name} m_values is empty ")

            self.controller.log_info(fl_ctx, f"task {self.task_name} control flow round = {task_flow_round}.")
            self.shareable.set_header(FOConstants.TASK_FLOW_ROUND, task_flow_round)

            if task_flow_round == 1:
                client = fl_ctx.get_engine().get_clients()[0]
                pivots = self.client_medians[client.name]
                self.shareable[FOConstants.PIVOTS] = pivots
            else:
                self.random_select_flow(abort_signal, fl_ctx)

            self.median_size_collection_flow(abort_signal, fl_ctx)
            self.median_data_purge_flow(abort_signal, fl_ctx)
            self.controller.log_info(fl_ctx, f"task {self.task_name} control flow end.")
            task_flow_round += 1

    def random_select_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        """
            random select one server, and random select one value ( called it r-value) as median approximation
        """
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow random_select_flow started.")
        self.task_name = FOConstants.AGGR_MEDIAN_RANDOM_TASK

        clients = fl_ctx.get_engine().get_clients()
        import random

        random.shuffle(clients)
        task = Task(name=self.task_name, data=self.shareable, result_received_cb=self.task_results_cb)
        self.controller.send_and_wait(
            task=task,
            targets=clients[:1],
            fl_ctx=fl_ctx,
            abort_signal=abort_signal,
        )
        self.random_select_post_fn(fl_ctx)
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow random_select_flow end.")

    def random_select_post_fn(self, fl_ctx: FLContext):
        self.controller.log_info(fl_ctx, f"random_select_post_fn(), result={self.result}")

        for client_name in self.result:
            stats = self.result[client_name][FeatureStatsConstants.STATS]
            if stats and FOConstants.PIVOTS in stats:
                r_values = stats[FOConstants.PIVOTS]
                self.shareable[FOConstants.PIVOTS] = r_values
            else:
                self.controller.log_info(fl_ctx, f"process Client {client_name} has NO stats result")

    def get_pivots(self) -> Union[Dict[str, float], None]:
        if FOConstants.PIVOTS in self.shareable:
            return self.shareable[FOConstants.PIVOTS]
        else:
            return None

    def median_size_collection_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        """
            send the random selected r (median approximation) to all servers
            and collect the size of elements that's greater than r (r-values)
            the returned size is called m (m-values)
        """
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow median_size_collection_flow started.")
        self.task_name = FOConstants.AGGR_MEDIAN_SIZE_COLL_TASK
        task = Task(name=self.task_name, data=self.shareable, result_received_cb=self.task_results_cb)
        clients = fl_ctx.get_engine().get_clients()

        self.controller.broadcast_and_wait(
            task=task,
            targets=None,
            min_responses=len(clients),
            fl_ctx=fl_ctx,
            wait_time_after_min_received=1,
            abort_signal=abort_signal,
        )
        self.median_size_collect_post_fn(fl_ctx)
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow median_size_collection_flow end.")

    def median_size_collect_post_fn(self, fl_ctx: FLContext):
        k_values = self.shareable[FOConstants.K_VALUES]
        m_values = {}
        l_values = {}
        e_values = {}

        self.shareable[FOConstants.MEDIAN_ACTION] = {}

        def set_value(col: str, x: {}, v: int):
            if col in x:
                x[feat_name] += v
            else:
                x[feat_name] = v

        for client_name in self.result:
            stats = self.result[client_name][FeatureStatsConstants.STATS][FOConstants.PIVOT_SIZES]
            for feat_name in stats:
                (m, e, l) = stats[feat_name]
                set_value(feat_name, m_values, m)
                set_value(feat_name, l_values, l)
                set_value(feat_name, e_values, e)

        # stop check
        delta = {}
        pivot_sizes = {}
        for feat_name in e_values:
            pivot_sizes[feat_name] = (m_values[feat_name], e_values[feat_name], l_values[feat_name])

            if e_values[feat_name] >= abs(m_values[feat_name] - l_values[feat_name]):
                self.shareable[FOConstants.MEDIAN_ACTION].update(
                    {feat_name: FOConstants.STOP_ACTION}
                )
            else:
                m_ratio = m_values[feat_name] / (m_values[feat_name] + l_values[feat_name] + e_values[feat_name])
                l_ratio = l_values[feat_name] / (m_values[feat_name] + l_values[feat_name] + e_values[feat_name])
                if abs(m_ratio - 0.5) < 0.005 or abs(l_ratio - 0.5) < 0.005:
                    self.shareable[FOConstants.MEDIAN_ACTION].update(
                        {feat_name: FOConstants.STOP_ACTION}
                    )
                else:
                    delta[feat_name] = m_values[feat_name] + e_values[feat_name] - k_values[feat_name]
                    if delta[feat_name] < 0:
                        k_values[feat_name] = k_values[feat_name] - m_values[feat_name] - e_values[feat_name]
                        self.shareable[FOConstants.MEDIAN_ACTION].update(
                            {feat_name: FOConstants.DISCARD_GREATER_SET_ACTION}
                        )
                    elif delta[feat_name] > 0:
                        self.shareable[FOConstants.MEDIAN_ACTION].update(
                            {feat_name: FOConstants.DISCARD_LESS_SET_ACTION}
                        )
                    else:
                        self.shareable[FOConstants.MEDIAN_ACTION].update(
                            {feat_name: FOConstants.STOP_ACTION}
                        )

        self.shareable[FOConstants.K_VALUES] = k_values
        self.shareable[FOConstants.PIVOT_SIZES] = pivot_sizes

    def median_data_purge_flow(self, abort_signal: Signal, fl_ctx: FLContext):
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow median_data_purge_flow started.")
        self.task_name = FOConstants.AGGR_MEDIAN_DATA_PURGE_TASK
        task = Task(name=self.task_name, data=Shareable(), result_received_cb=self.task_results_cb)
        clients = fl_ctx.get_engine().get_clients()

        self.controller.broadcast_and_wait(
            task=task,
            targets=None,
            min_responses=len(clients),
            fl_ctx=fl_ctx,
            wait_time_after_min_received=1,
            abort_signal=abort_signal,
        )
        self.controller.log_info(fl_ctx, f"task {self.task_name} control flow median_data_purge_flow end.")

    def stop_actions(self) -> bool:
        if FOConstants.MEDIAN_ACTION in self.shareable:
            feature_actions = self.shareable[FOConstants.MEDIAN_ACTION]
            greater_k_values = [
                feat
                for feat in feature_actions
                if feature_actions[feat] == FOConstants.DISCARD_GREATER_SET_ACTION
            ]
            if len(greater_k_values) > 0:
                return False
            else:
                lesser_k_values = [
                    feat
                    for feat in feature_actions
                    if feature_actions[feat] == FOConstants.DISCARD_LESS_SET_ACTION
                ]
                if len(lesser_k_values) > 0:
                    return False
                else:
                    return True
        else:
            return False
