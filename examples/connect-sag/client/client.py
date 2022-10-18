
import os
import time

import numpy as np

from nvflare.apis.dxo import DXO, DataKind
from nvflare.apis.fl_constant import FLContextKey, ReturnCode
from nvflare.apis.fl_context import FLContext
from nvflare.apis.shareable import Shareable, make_reply
from nvflare.apis.signal import Signal
from nvflare.app_common.abstract.model import ModelLearnable
from nvflare.app_common.app_constant import AppConstants
from nvflare.security.logging import secure_format_exception
from .constants import NPConstants


class NPTrainer:

    def __init__(
            self,
            client_name: str,
            delta=1,
            sleep_time=0,
            train_task_name=AppConstants.TASK_TRAIN,
            submit_model_task_name=AppConstants.TASK_SUBMIT_MODEL,
            model_name="best_numpy.npy",
            model_dir="model",
    ):

        if not (isinstance(delta, float) or isinstance(delta, int)):
            raise TypeError("delta must be an instance of float or int.")

        self._delta = delta
        self._model_name = model_name
        self._model_dir = model_dir
        self._sleep_time = sleep_time
        self._train_task_name = train_task_name
        self._submit_model_task_name = submit_model_task_name
        self.client_name = client_name

    def _train(self, parameters: dict, meta: dict):

        # Information about workflow is retrieved from the shareable header.
        current_round = meta.get(AppConstants.CURRENT_ROUND, None)
        total_rounds = meta.get(AppConstants.NUM_ROUNDS, None)
        data_kind = meta.get("data_kind", None)
        if data_kind != DataKind.WEIGHTS:
            return make_reply(ReturnCode.BAD_TASK_DATA)
        np_data = parameters["data"]

        # Doing some dummy training.
        if np_data:
            if NPConstants.NUMPY_KEY in np_data:
                np_data[NPConstants.NUMPY_KEY] += self._delta
            else:
                print("numpy_key not found in model.")
                return make_reply(ReturnCode.BAD_TASK_DATA)
        else:
            print("No model weights found in shareable.")
            return make_reply(ReturnCode.BAD_TASK_DATA)

        # Save local numpy model
        try:
            self._save_local_model(np_data)
        except Exception as e:
            print(f"Exception in saving local model: {secure_format_exception(e)}.")

        outgoing_dxo = DXO(data_kind=data_kind, data=np_data, meta={})
        return outgoing_dxo

    def _submit_model(self):
        # Retrieve the local model saved during training.
        np_data = None
        try:
            np_data = self._load_local_model()
        except Exception as e:
            print(f"Unable to load model: {secure_format_exception(e)}")

        # Create DXO and shareable from model data.
        model_shareable = Shareable()
        if np_data:
            outgoing_dxo = DXO(data_kind=DataKind.WEIGHTS, data=np_data)
            model_shareable = outgoing_dxo.to_shareable()
        else:
            # Set return code.
            print("local model not found.")
            model_shareable.set_return_code(ReturnCode.EXECUTION_RESULT_ERROR)

        return model_shareable

    def execute( self, task_name: str, shareable: Shareable) -> Shareable:
        count, interval = 0, 0.5
        while count < self._sleep_time:
            time.sleep(interval)
            count += interval

        print(f"Task name: {task_name}")
        try:
            if task_name == self._train_task_name:
                return self._train(parameters=shareable)
            elif task_name == self._submit_model_task_name:
                return self._submit_model()
            else:
                # If unknown task name, set RC accordingly.
                return make_reply(ReturnCode.TASK_UNKNOWN)
        except Exception as e:
            print(f"Exception in NPTrainer execute: {secure_format_exception(e)}.")
            return make_reply(ReturnCode.EXECUTION_EXCEPTION)

    def _load_local_model(self):
        engine = fl_ctx.get_engine()
        job_id = fl_ctx.get_prop(FLContextKey.CURRENT_RUN)
        run_dir = engine.get_workspace().get_run_dir(job_id)
        model_path = os.path.join(run_dir, self._model_dir)

        model_load_path = os.path.join(model_path, self._model_name)
        try:
            np_data = np.load(model_load_path)
        except Exception as e:
            print(f"Unable to load local model: {secure_format_exception(e)}")
            return None

        model = ModelLearnable()
        model[NPConstants.NUMPY_KEY] = np_data

        return model

    def _save_local_model(self, model: dict):
        # Save local model
        engine = fl_ctx.get_engine()
        job_id = fl_ctx.get_prop(FLContextKey.CURRENT_RUN)
        run_dir = engine.get_workspace().get_run_dir(job_id)
        model_path = os.path.join(run_dir, self._model_dir)
        if not os.path.exists(model_path):
            os.makedirs(model_path)

        model_save_path = os.path.join(model_path, self._model_name)
        np.save(model_save_path, model[NPConstants.NUMPY_KEY])
        print(f"Saved numpy model to: {model_save_path}")
