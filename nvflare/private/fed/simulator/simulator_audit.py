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

from nvflare.fuel.sec.audit import Auditor


class SimulatorAuditor(Auditor):
    def __init__(self):
        pass

    def add_event(self, user: str, action: str, ref: str = "", msg: str = "") -> str:
        pass

    def add_job_event(
        self, job_id: str, scope_name: str = "", task_name: str = "", task_id: str = "", ref: str = "", msg: str = ""
    ) -> str:
        pass

    def close(self):
        pass
