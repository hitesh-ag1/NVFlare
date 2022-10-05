import base64


class Communicator:
    def send(self, inputs: dict) -> bool:
        return True

    pass


class Connector:
    def __init__(self, communicator: Communicator):
        self.communicator = communicator

    def setup(self, inputs: dict):
        inputs["coord_task"] = "setup"
        self.communicator.send(inputs)

    def broadcast(self, inputs: dict):
        inputs["coord_task"] = "broadcast"
        self.communicator.send(inputs)



