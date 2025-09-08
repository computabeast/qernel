from __future__ import annotations
from typing import Any
import cirq
from qernel import QernelClient, QernelConfig


def main() -> int:
    job_id = "242"  # This job has trial_result and simulator_state artifacts
    client = QernelClient(QernelConfig())

    # Create a mock response object with the artifact paths from the server response
    # This simulates what we'd get from the streaming response
    class MockResponse:
        def __init__(self):
            self.analysis = {
                "pipeline": [
                    {
                        "name": "execute.simulator",
                        "output": {
                            "artifact_storage": {
                                "stored_artifacts": {
                                    "trial_result": "artifacts/e831e513-b95a-4211-b11a-d686a4b91dfb/242/trial_result.pkl.gz",
                                    "simulator_state": "artifacts/e831e513-b95a-4211-b11a-d686a4b91dfb/242/simulator_state.pkl.gz"
                                }
                            }
                        }
                    }
                ]
            }

    # Load artifacts using the paths from the server response
    print("Loading artifacts from job 242 using paths from server response...")
    try:
        mock_response = MockResponse()
        artifacts = client.load_artifacts_from_response(mock_response)
        print(f"Successfully loaded {len(artifacts)} artifacts: {list(artifacts.keys())}")
        
    except Exception as e:
        print(f"Error loading artifacts: {e}")
        return 1

    # Access the artifacts
    trial_result = artifacts.get("trial_result")
    simulator_state = artifacts.get("simulator_state")

    if trial_result:
        print("Found trial_result artifact")
        print(trial_result.histogram(key="m"))
    else:
        print("trial_result artifact not found")

    if simulator_state:
        print("Found simulator_state artifact")
        circuit = simulator_state.get("circuit")
        if circuit:
            print(f"Circuit has {len(circuit)} operations")
    else:
        print("simulator_state artifact not found")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
