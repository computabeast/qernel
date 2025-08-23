#!/usr/bin/env python3
"""
Test Algorithm for Qernel Visualization
This demonstrates the code snippets feature in the visualization window.
"""

import cirq
from qernel import Algorithm


class TestAlgorithm(Algorithm):
    """Test quantum algorithm for visualization demo."""
    
    def get_name(self) -> str:
        """Return the human-readable name of the algorithm."""
        return "Test Algorithm"
    
    def get_type(self) -> str:
        """Return the algorithm type identifier."""
        return "test_algorithm"
    
    def build_circuit(self, params: dict) -> cirq.Circuit:
        """
        Build a test quantum circuit.
        
        Args:
            params: Dictionary containing algorithm parameters from spec.yaml
        
        Returns:
            A Cirq Circuit object
        """
        # Get parameters from spec
        num_qubits = params.get('num_qubits', 3)
        depth = params.get('depth', 5)
        
        # Create qubits
        q = cirq.LineQubit.range(num_qubits)
        
        # Build circuit
        circuit = cirq.Circuit()
        
        for i in range(depth):
            # Add some gates
            circuit.append(cirq.H(q[0]))
            if num_qubits > 1:
                circuit.append(cirq.CNOT(q[0], q[1]))
            if num_qubits > 2:
                circuit.append(cirq.T(q[2]))
        
        return circuit


# Create an instance for testing
algorithm = TestAlgorithm()
