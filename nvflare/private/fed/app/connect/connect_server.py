import socketserver

from nvflare.private.fed.app.connect.connect_server_req_handler import ConnectServerReqHandler


class ConnectServer(socketserver.TCPServer):

    def __init__(self, host: str, port: int, fed_server):
        super(ConnectServer, self).__init__((host, port), ConnectServerReqHandler)
        self.fed_server = fed_server

    def start(self):
        print("*************************************************")
        print("**************** ConnectServer started **********")
        print("*************************************************")
        self.serve_forever()

    def finish_request(self, request, client_address):
        """Finish one request by instantiating RequestHandlerClass."""
        print("***************************** finish_request ****************")
        ConnectServerReqHandler(request, client_address, self, self.fed_server)


if __name__ == "__main__":
    ConnectServer("127.0.0.1", 9999, None).start()
