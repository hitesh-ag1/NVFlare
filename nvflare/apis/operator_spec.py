from abc import ABC

from nvflare.apis.fl_component import FLComponent


class OperatorSpec(FLComponent, ABC):

    def op(self, parameters: dict, result_received_cb: callable):
        pass

