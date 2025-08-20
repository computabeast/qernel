"""
Algorithm Template - Edit this file to implement your quantum algorithm.

This template provides a simple interface for implementing quantum algorithms
that can be executed by the quantum resource estimation system.

Requirements:
- Your algorithm must inherit from Algorithm
- You must implement get_name(), get_type(), and build_circuit()
- build_circuit() must return a Cirq Circuit object
- Use the params dictionary to access configuration from spec.yaml
"""

import cirq
from qernel import Algorithm


class MyAlgorithm(Algorithm):
    """Template for implementing a quantum algorithm."""
    
    def get_name(self) -> str:
        """Return the human-readable name of your algorithm."""
        return "My Algorithm"
    
    def get_type(self) -> str:
        """Return the algorithm type identifier."""
        return "my_algorithm"
    
    def build_circuit(self, params: dict) -> cirq.Circuit:
        """
        Build your quantum circuit here.
        
        Args:
            params: Dictionary containing parameters from spec.yaml
                   Common keys: epsilon, payoff, hardware_preset
        
        Returns:
            A Cirq Circuit object
        """
        # Example: Create a simple circuit
        # Replace this with your actual algorithm implementation
        
        # Access parameters from spec.yaml
        epsilon = params.get('epsilon', 0.01)
        payoff = params.get('payoff', 'max')
        
        # Create qubits
        q = cirq.LineQubit.range(3)
        
        # Build your circuit
        circuit = cirq.Circuit(
            cirq.H(q[0]),           # Hadamard gate
            cirq.CNOT(q[0], q[1]),  # CNOT gate
            cirq.T(q[1]),           # T gate
        )
        
        return circuit
    
    def validate_params(self, params: dict) -> None:
        """
        Optional: Add custom parameter validation.
        
        This method is called before build_circuit() to validate parameters.
        Raise ValueError if parameters are invalid.
        """
        # Example validation
        if 'epsilon' in params and params['epsilon'] <= 0:
            raise ValueError("epsilon must be positive")
        
        if 'payoff' in params and params['payoff'] not in ['max', 'min']:
            raise ValueError("payoff must be 'max' or 'min'")


# Create an instance of your algorithm
# This is used for testing and by the backend
algorithm = MyAlgorithm()
