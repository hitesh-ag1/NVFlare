from nvflare.apis.fl_context import FLContext
from nvflare.apis.impl.broadcast import Broadcast
from nvflare.apis.impl.controller import ClientTask
from nvflare.private.fed.server.fed_server import FederatedServer
from .messaage import create_message


def broadcast_handler(parameters: dict, request, fed_server: FederatedServer):
    print("parameters = ", parameters)
    #
    broadcast_op = Broadcast(fed_server.fl_ctx)
    broadcast_op.op(parameters, result_received_cb)
    fed_server.engine.job_runner.run(fed_server.fl_ctx)

    #
    client_name = "site-1" #client_task.client.name
    task_name = broadcast_op.get_task_name(parameters)
    result = "fake result"
    client_task_results = {
        "client": client_name,
        "task": task_name,
        "result": result
    }
    response_in_bytes = create_message(client_task_results, "text/json", "utf-8")
    # client_task.result = None

    request.sendall(response_in_bytes)


def result_received_cb(client_task: ClientTask, fl_ctx: FLContext):
    print(f"Processing {client_task.task.name} result_received_cb from client { client_task.client.name}")
    return client_task
