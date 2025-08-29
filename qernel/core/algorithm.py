"""
Algorithm base class for quantum algorithm plugins.

This provides a clean interface for users to implement quantum algorithms
without needing to understand the internal plugin system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class Algorithm(ABC):
    """Base class for quantum algorithm implementations."""

    @abstractmethod
    def get_name(self) -> str:
        """Return the human-readable name of the algorithm."""
        pass

    @abstractmethod
    def get_type(self) -> str:
        """Return the algorithm type identifier."""
        pass

    @abstractmethod
    def build_circuit(self, params: Dict[str, Any]) -> Any:
        """
        Build the quantum circuit for this algorithm.

        Args:
            params: Dictionary containing algorithm parameters
                   Keys may include: epsilon, payoff, hardware_preset, etc.

        Returns:
            A Cirq Circuit object
        """
        pass
