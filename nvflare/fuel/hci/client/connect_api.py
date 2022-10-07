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

from typing import List, Optional
import json

from nvflare.fuel.hci.client.api import AdminAPI
from nvflare.fuel.hci.client.fl_admin_api_spec import APISyntaxError


class ConnectAPI(AdminAPI):
    def __init__(
        self,
        ca_cert: str = "",
        client_cert: str = "",
        client_key: str = "",
        upload_dir: str = "",
        cmd_modules: Optional[List] = None,
        user_name: str = None,
        debug=False,
    ):
        super().__init__(
            self,
            ca_cert=ca_cert,
            client_cert=client_cert,
            client_key=client_key,
            upload_dir=upload_dir,
            download_dir="",
            cmd_modules=cmd_modules,
            service_finder=None,
            user_name=user_name,
            poc=True,
            debug=debug,
        )
        self.upload_dir = upload_dir
        self._error_buffer = None

    @staticmethod
    def _validate_input(job_folder: str):
        if not job_folder:
            raise APISyntaxError("job_folder is required but not specified.")
        if not isinstance(job_folder, str):
            raise APISyntaxError("job_folder must be str but got {}.".format(type(job_folder)))

    def broadcast(self, job_folder: str):
        ConnectAPI._validate_input(job_folder)
        cmd = "broadcast" + " " + job_folder
        reply = self.do_command(cmd)
        return reply

    def setup(self, inputs: dict):
        cmd = "broadcast" + 
        reply = self.do_command(cmd)
        return reply


