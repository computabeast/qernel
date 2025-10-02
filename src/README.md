## Agent Overview

The main value of the Qernel CLI is to decrease the time it takes to convert quantum concepts in literature and math to runnable quantum programs. The current CLI offers a streamlined way to do so:

```bash 
# Replace my-project with the name of your project
qernel new my-project --template
```

This will create a Git repository named `my-project` with the following structure:

```
my-project/
├── README.md
├── .gitignore
├── src/                       # Source code directory (where you work from)
│   ├── __init__.py
│   ├── main.py                # Main implementation file
│   └── tests.py               # Test file with basic pytest setup
├── .qernel/                   # Qernel-specific working directory (git-ignored)
│   ├── README.md
│   ├── spec.md                # Project spec to feed into the agent
│   ├── benchmark.md           # Benchmarking spec to feed into the agent
│   ├── qernel.yaml            # Qernel agent configuration file 
│   ├── requirements.txt       # Python dependencies
│   └── .venv/                 # Python virtual environment (created automatically)
└── .git/                      # Git repository (initialized automatically)
```

You can then prototype by pasting instructions in `.qernel/spec.md`, or automatically download and prototype a paper from [the arXiv](https://arxiv.org). A more comprehensive guide to using the prototype feature can be found in [src/README.md](./src/README.md).

```
qernel prototype
```