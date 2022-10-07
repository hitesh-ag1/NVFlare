import base64
import os.path
from typing import io

from nvflare.app_common.app_constant import AppConstants

def load_initial_global_model():
    return {}


def prepare_inputs(_global_weights, current_round, total_rounds):
    inputs = dict()
    inputs["global_weights"] = _global_weights
    inputs.update({
                     AppConstants.CURRENT_ROUND: current_round,
                     AppConstants.NUM_ROUNDS: total_rounds
                     AppConstants.CONTRIBUTION_ROUND: current_round
                   }
                  )

    return inputs


def update_model(aggr_result):
    return dict()

def broadcast_and_wait(inputs: dict):
    from nvflare.fuel.hci.client.api import
    return {}


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

    for current_round in range (start_round, total_rounds):

        print(f"Round {current_round} started.")
        # Create train_task
        inputs: dict = prepare_inputs(_global_weights, current_round, total_rounds)

        client_results = broadcast_and_wait(inputs)

        aggr_result = aggregate(client_results)

        _global_weights = update_model(aggr_result)

        print(f"Round {current_round} finished.")

def setup():
    # ask Server Service to create a coordinator specific for this job
    # serialize client code adn transfer client files to server and ask
    # Server Service to deploy Client Executors and executor ids
    pass

def main():
    setup()
    train()


if __name__ == "__main__":
    main()
