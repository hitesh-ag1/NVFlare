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

import os

import nvflare.fuel.hci.file_transfer_defs as ftd
from nvflare.fuel.hci.base64_utils import (
    bytes_to_b64str,
)
from nvflare.fuel.hci.cmd_arg_utils import join_args
from nvflare.fuel.hci.reg import CommandEntry, CommandModule, CommandModuleSpec, CommandSpec
from nvflare.fuel.utils.zip_utils import split_path, zip_directory_to_bytes
from .api_spec import CommandContext
from .api_status import APIStatus


class ConnectAPICommands(CommandModule):
    """Command module with commands relevant to ConnectCommands."""

    def __init__(self, upload_dir: str):
        if not os.path.isdir(upload_dir):
            raise ValueError("upload_dir {} is not a valid dir".format(upload_dir))

        self.upload_dir = upload_dir
        self.cmd_handlers = {
            ftd.UPLOAD_FOLDER_FQN: self.upload_folder,
        }

    def get_spec(self):
        return CommandModuleSpec(
            name="connect transfer",
            cmd_specs=[
                CommandSpec(
                    name="upload_folder",
                    description="setup client code to the servert",
                    usage="setup client_folder",
                    handler_func=self.upload_folder,
                    visible=False,
                ),
                CommandSpec(
                    name="broadcast",
                    description="send broadcast inputs to server",
                    usage="broadcast",
                    handler_func=None,
                    visible=False,
                ),
             ],
        )

    def generate_module_spec(self, server_cmd_spec: CommandSpec):
        """
        Generate a new module spec based on a server command

        Args:
            server_cmd_spec:

        Returns:

        """
        # print('generating cmd module for {}'.format(server_cmd_spec.client_cmd))
        if not server_cmd_spec.client_cmd:
            return None

        handler = self.cmd_handlers.get(server_cmd_spec.client_cmd)
        if handler is None:
            # print('no cmd handler found for {}'.format(server_cmd_spec.client_cmd))
            return None

        return CommandModuleSpec(
            name=server_cmd_spec.scope_name,
            cmd_specs=[
                CommandSpec(
                    name=server_cmd_spec.name,
                    description=server_cmd_spec.description,
                    usage=server_cmd_spec.usage,
                    handler_func=handler,
                    visible=True,
                )
            ],
        )

    def upload_folder(self, args, ctx: CommandContext):
        cmd_entry = ctx.get_command_entry()
        assert isinstance(cmd_entry, CommandEntry)
        if len(args) != 2:
            return {"status": APIStatus.ERROR_SYNTAX, "details": "usage: {}".format(cmd_entry.usage)}

        folder_name = args[1]
        if folder_name.endswith("/"):
            folder_name = folder_name.rstrip("/")

        full_path = os.path.join(self.upload_dir, folder_name)
        if not os.path.isdir(full_path):
            return {"status": APIStatus.ERROR_RUNTIME, "details": f"'{full_path}' is not a valid folder."}

        # zip the data
        data = zip_directory_to_bytes(self.upload_dir, folder_name)

        folder_name = split_path(full_path)[1]
        b64str = bytes_to_b64str(data)
        parts = [cmd_entry.full_command_name(), folder_name, b64str]
        command = join_args(parts)
        api = ctx.get_api()
        return api.server_execute(command)
