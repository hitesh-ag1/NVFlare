import socketserver
import threading

from .connect_action_handlers import broadcast_handler
from .messaage import unpack_message, json_encode


class ConnectServerReqHandler(socketserver.BaseRequestHandler):
    """
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def get_action_handler(self):
        return {
            "broadcast": broadcast_handler,
        }

    def handle(self):
        # self.request is the TCP socket connected to the client
        print("hello")
        received = self.request.recv(2048)
        print("from {} received:".format(self.client_address[0]))
        headers, content = unpack_message(received)
        content_type = headers["content-type"]
        if content_type == "text/json":
            action = content["action"]
            parameters = content["parameters"]
            action_handler = self.get_action_handler().get(action, None)
            if action_handler:
                threading.Thread(target=action_handler, args=[parameters, self.request]).start()

        # just send back the same data, but upper-cased
        # self.request.sendall(received)
