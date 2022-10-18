import base64
import os.path
from typing import io

from nvflare.app_common.app_constant import AppConstants
from nvflare.private.fed.app.connect.connect_api import ConnectAPI


def load_initial_global_model():
    return {}


def update_model(aggr_result):
    return dict()


def broadcast(inputs: dict):
    conn_api = ConnectAPI()
    return conn_api.broadcast(inputs)


def aggregate(client_results):
    return {}


def train():
    min_clients = 2
    total_rounds = 3
    start_round = 0
    wait_time_after_min_received = 0
    task_name = "train"
    train_timeout = 6000
    _global_weights = load_initial_global_model()

    for current_round in range(start_round, total_rounds):
        print(f"Round {current_round} started.")
        # Create train_task
        inputs = {
            "global_weights": _global_weights,
            AppConstants.CURRENT_ROUND: current_round,
            AppConstants.NUM_ROUNDS: total_rounds,
            AppConstants.CONTRIBUTION_ROUND: current_round,
            "nvflare.task.name": task_name,
            "nvflare.task.wait_time_after_min_received": wait_time_after_min_received,
            "nvflare.task.timeout": train_timeout,
            "nvflare.task.client.min_responses": min_clients
        }

        client_results = broadcast(inputs)
        print(client_results)
        print(f"Round {current_round} finished.")


def setup():
    # serialize client code adn transfer client files to server and ask
    # Server Service to deploy Client Executors and executor ids
    pass


def main():
    setup()
    train()


if __name__ == "__main__":
    main()
