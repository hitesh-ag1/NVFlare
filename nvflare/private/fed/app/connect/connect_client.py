import socket
from .messaage import create_message, unpack_message


def send_recv(host, port, data, content_type: str, content_encoding):
    message = create_message(data, content_type, content_encoding)

    # create a TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # connect to server
        sock.connect((host, port))
        # send data
        sock.sendall(message)
        print("Sent:     {}".format(data))
        # receive data back from the server
        received = sock.recv(2048)
        print("Received: {}".format(received))
        return received
    finally:
        # shut down
        sock.close()


