<div align="center">
<img alt="Qernel logo" width="96px" src="https://www.dojoquantum.com/_next/image?url=%2Fquantum-computing.png&w=96&q=75">
<br>

An agentic, virtual kernel for efficient programming of quantum systems

[![Compatible with Python versions 3.9 and higher](https://img.shields.io/badge/Python-3.9+-6828b2.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Qernel project on PyPI](https://img.shields.io/pypi/v/qernel.svg?logo=python&logoColor=white&label=PyPI&style=flat-square&color=9d3bb8)](https://pypi.org/project/qernel)

`pip install qernel`
</div>

### Creating Your Algorithm

Create your algorithm class by inheriting from the `Algorithm` base class:

```python
import cirq
from qernel import Algorithm

class MyAlgorithm(Algorithm):
    """
    A docstring describing what you'd like to do to your algorithm, ie. what error mitigation techniques, 
    what you want displayed, etc. 

    Ex:
    1. Error mitigation, ZNE, applied to the entire circuit.
    2. I'd also like the circuit displayed in 3D in cirq-web.
    """

    def get_name(self) -> str:
        return "My Algorithm"
    
    def get_type(self) -> str:
        return "my_algorithm"
    
    def build_circuit(self, params: dict) -> cirq.Circuit:
        # Your quantum circuit implementation here
        q = cirq.LineQubit.range(2)
        circuit = cirq.Circuit(
            cirq.H(q[0]),
            cirq.CNOT(q[0], q[1])
        )
        return circuit
```

### API Configuration

Create a `.env` file in your project root and add:

```bash
QERNEL_API_KEY=your_api_key_here
```

### Using the Client

```python
from qernel import Algorithm, QernelClient

# Create your algorithm instance
algorithm = MyAlgorithm()

# Create and use the client (streaming API)
client = QernelClient()
transcript = client.run_stream(algorithm_instance=algorithm, params={}, visualize=False)
```

OR with custom configuration:

```python
from qernel.core.client import QernelConfig

config = QernelConfig(api_key="your_api_key_here")
client = QernelClient(config)
transcript = client.run_stream(algorithm_instance=algorithm, params={}, visualize=False)
```

### Using Visualization

Qernel includes a real-time visualization system that provides a live window into quantum algorithm execution. To use it:

```python
from qernel import Algorithm, QernelClient

# Create your algorithm instance
algorithm = MyAlgorithm()

# Create client and run with real-time visualization
client = QernelClient()
transcript = client.run_stream(algorithm_instance=algorithm, params={}, visualize=True)
```

### Supported packages

<div align="left">

<table>
<tr>
<th align="left">Use Case</th>
<th align="left">Packages</th>
</tr>
<tr>
<td>Resource estimation</td>
<td><a href="https://github.com/quantumlib/qualtran">Qualtran</a></td>
</tr>
<tr>
<td>Error mitigation</td>
<td><a href="https://github.com/unitaryfund/mitiq">Mitiq</a></td>
</tr>
<tr>
<td>Circuit design</td>
<td>
<a href="https://github.com/quantumlib/cirq">Cirq</a><br>
<a href="https://github.com/Qiskit/qiskit">Qiskit</a> (TODO)<br>
<a href="https://github.com/PennyLaneAI/pennylane">PennyLane</a> (TODO)
</td>
</tr>
</table>

</div>