"""
Hello World Algorithm Example

This demonstrates how to create a simple quantum algorithm plugin for Qernel.
Users can use this as a template for their own algorithms.
"""

import cirq
from qernel import Algorithm


class HelloWorldAlgorithm(Algorithm):
    """Hello World quantum algorithm example."""
    
    def get_name(self) -> str:
        """Return the human-readable name of the algorithm."""
        return "Hello World"
    
    def get_type(self) -> str:
        """Return the algorithm type identifier."""
        return "hello_world"
    
    def build_circuit(self, params: dict) -> cirq.Circuit:
        """
        Build the Hello World quantum circuit.
        
        Args:
            params: Dictionary containing algorithm parameters from spec.yaml
        
        Returns:
            A Cirq Circuit object
        """
        # Create a simple 3-qubit circuit
        q = cirq.LineQubit.range(3)
        
        circuit = cirq.Circuit(
            cirq.H(q[0]),           # Hadamard on first qubit
            cirq.CCX(q[0], q[1], q[2]),  # Toffoli gate
            cirq.T(q[2]) ** -1,     # T dagger on third qubit
        )
        
        return circuit


# Create an instance for testing
algorithm = HelloWorldAlgorithm()
