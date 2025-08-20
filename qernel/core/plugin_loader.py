"""
Plugin loader for dynamically discovering and loading quantum algorithms.
"""

import importlib.util
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class PluginLoader:
    """Loads quantum algorithm plugins dynamically."""
    
    @staticmethod
    def load_algorithm_from_spec(spec_file: str) -> Any:
        """
        Load an algorithm based on the specification file.
        
        Args:
            spec_file: Path to the YAML specification file
        
        Returns:
            The algorithm instance
        """
        # Load the specification
        with open(spec_file, 'r') as f:
            spec = yaml.safe_load(f)
        
        algorithm_name = spec['algorithm']['name']
        
        # Look for algorithm file in the same directory as spec
        spec_dir = Path(spec_file).parent
        algorithm_file = spec_dir / f"{algorithm_name}.py"
        
        if not algorithm_file.exists():
            raise FileNotFoundError(f"Algorithm file not found: {algorithm_file}")
        
        # Load the algorithm module
        spec = importlib.util.spec_from_file_location(algorithm_name, algorithm_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get the algorithm instance
        if hasattr(module, 'algorithm'):
            return module.algorithm
        else:
            raise AttributeError(f"No 'algorithm' instance found in {algorithm_file}")
    
    @staticmethod
    def discover_algorithms() -> Dict[str, str]:
        """
        Discover all algorithms in the current directory.
        
        Returns:
            Dictionary mapping algorithm names to their spec file paths
        """
        algorithms = {}
        
        # Look for spec.yaml files
        for spec_file in Path('.').glob('**/spec.yaml'):
            try:
                with open(spec_file, 'r') as f:
                    spec = yaml.safe_load(f)
                
                algorithm_name = spec['algorithm']['name']
                algorithms[algorithm_name] = str(spec_file)
                
            except Exception as e:
                print(f"Warning: Could not load spec file {spec_file}: {e}")
        
        return algorithms
