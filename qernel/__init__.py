"""
Qernel - Quantum Algorithm Plugin System

A simple system for creating quantum algorithm plugins that can be executed
by the quantum resource estimation system.

Usage:
    from qernel import Algorithm, QernelClient
    
    class MyAlgorithm(Algorithm):
        def get_name(self) -> str:
            return "My Algorithm"
        
        def get_type(self) -> str:
            return "my_algorithm"
        
        def build_circuit(self, params: dict) -> cirq.Circuit:
            # Your circuit implementation here
            pass
    
    # Create client and run algorithm
    client = QernelClient()
    result = client.run_algorithm(MyAlgorithm())
"""

from .core.algorithm import Algorithm
from .core.client import QernelClient

__all__ = ["Algorithm", "QernelClient"]
