from __future__ import annotations
from typing import Any
import cirq
from qernel import QernelClient, QernelConfig


def main() -> int:
    job_id = "197"
    client = QernelClient(QernelConfig())

    artifacts = client.load_artifacts_sequential(
        job_id, ["trial_result", "simulator_state"]
    )
    trial_result: Any = artifacts["trial_result"]
    simulator_state: Any = artifacts["simulator_state"]

    circuit = simulator_state.get("circuit")
    print(circuit)

    # Retrieve existing measurement results
    print(trial_result.histogram(key="m"))

    # Continue where you left off
    qubits = circuit.all_qubits()
    print(qubits)
    circuit = cirq.Circuit(circuit.moments[:-1])  # Remove the measurement moment
    circuit.append(cirq.H(list(qubits)[0]))
    print(circuit)


if __name__ == "__main__":
    raise SystemExit(main())
