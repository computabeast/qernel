"""
Qernel - Quantum Algorithm Plugin System

A simple system for creating quantum algorithm plugins that can be executed
by the quantum resource estimation system.

Usage:
    from qernel import Algorithm
    
    class MyAlgorithm(Algorithm):
        def get_name(self) -> str:
            return "My Algorithm"
        
        def get_type(self) -> str:
            return "my_algorithm"
        
        def build_circuit(self, params: dict) -> cirq.Circuit:
            # Your circuit implementation here
            pass
"""

from .core.algorithm import Algorithm
from .core.client import QernelClient
from .core.plugin_loader import PluginLoader

__all__ = ["Algorithm", "QernelClient", "PluginLoader"]
