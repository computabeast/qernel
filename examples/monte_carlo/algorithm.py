"""
Monte Carlo algorithm example with amplitude estimation.

This demonstrates a more complex algorithm using amplitude estimation
for Monte Carlo expectation estimation.
"""

import math
import cirq
from qernel import Algorithm


class MonteCarloAlgorithm(Algorithm):
    """Monte Carlo expectation estimation using amplitude estimation."""
    
    def get_name(self) -> str:
        """Return the human-readable name of the algorithm."""
        return "Monte Carlo AE"
    
    def get_type(self) -> str:
        """Return the algorithm type identifier."""
        return "monte_carlo"
    
    def build_circuit(self, params: dict) -> cirq.Circuit:
        """
        Build the amplitude estimation circuit for Monte Carlo.
        
        Args:
            params: Dictionary containing algorithm parameters from spec.yaml
        
        Returns:
            A Cirq Circuit object
        """
        # Get parameters
        epsilon = params.get('epsilon', 0.01)
        
        # Choose AE depth ~ O(1/epsilon) (toy policy)
        n_iters = max(1, int(math.ceil(1.0 / float(epsilon))))
        n_state_qubits = 16
        n_work_qubits = 4
        
        # Build the amplitude estimation circuit
        circuit = self._build_qae_circuit(n_state_qubits, n_work_qubits, n_iters)
        
        return circuit
    
    def _build_qae_circuit(self, n_state_qubits: int, n_work_qubits: int, n_iters: int) -> cirq.Circuit:
        """
        Build an amplitude estimation circuit.
        
        This is a simplified implementation. In practice, you would implement
        proper state preparation A and Grover operator for your specific problem.
        """
        qs = cirq.LineQubit.range(n_state_qubits + n_work_qubits + 1)  # +1 ancilla
        
        anc = qs[-1]
        c = cirq.Circuit()
        c.append(cirq.H.on_each(*qs))
        
        for _ in range(n_iters):
            c.append(cirq.CZ(qs[0], anc))
        
        c.append(cirq.inverse(cirq.Circuit(cirq.H.on_each(*qs))))
        
        return c
    
    def validate_params(self, params: dict) -> None:
        """Validate Monte Carlo parameters."""
        epsilon = params.get('epsilon', 0.01)
        if epsilon <= 0 or epsilon >= 1:
            raise ValueError("epsilon must be between 0 and 1")


# Create an instance for testing
algorithm = MonteCarloAlgorithm()
