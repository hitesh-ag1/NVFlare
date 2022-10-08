import socketserver

from nvflare.private.fed.app.connect.connect_server_req_handler import ConnectServerReqHandler


class ConnectServer(socketserver.TCPServer):

    def __init__(self, host: str, port: int):
        super(ConnectServer, self).__init__((host, port), ConnectServerReqHandler)
        self.host = host
        self.port = port

    def start(self):
        print("*************************************************")
        print("**************** ConnectServer started **********")
        print("*************************************************")
        print("*************************************************")
        self.serve_forever()


if __name__ == "__main__":
    ConnectServer("127.0.0.1", 9999).start()
