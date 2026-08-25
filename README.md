# plugin-runtime-engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An extension runtime for composable systems: declare plugins as classes with capabilities, dependencies, and hook subscriptions — the runtime resolves startup order, fires lifecycle hooks, and guards every invocation.

## 🚀 Overview

The architecture core of the 2025 roadmap. `plugin-runtime-engine` turns features into **plugins**: subclasses declaring `name`, `version`, `depends_on`, and `capabilities()`. The runtime topologically sorts dependencies (cycles detected at resolution), boots in dependency order, wires subscribed hooks through a shared context, and dispatches capability calls only to active plugins. Shutdown reverses boot order so cleanup mirrors setup.

## ✨ Features

- **Declarative plugins:** class-level `name/version/depends_on/hooks_subscribed` + `capabilities()` map
- **Topological boot order:** dependencies start before dependents; cycles raise `DependencyCycleError`
- **Capability invocation:** typed lookup — missing capabilities list what *is* available
- **Hook registry:** plugins subscribe by name; context-wide emit fans out
- **Shared services:** `context.service("database")` gives controlled access to host resources
- **Reverse teardown:** shutdown order is the exact inverse of boot
- **Status report:** per-plugin state (`registered → active → stopped`) + setup timings
- **Zero dependencies**

## 🚧 Structure

```
plugin-runtime-engine/
├── src/plugin_runtime/
│   ├── __init__.py
│   └── core.py
├── tests/
│   └── test_core.py
├── README.md
└── pyproject.toml
```

## 📦 Installation

```bash
git clone https://github.com/supremeloki/plugin-runtime-engine.git
cd plugin-runtime-engine
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## 📋 Requirements

- Python 3.11+
- No runtime dependencies

## 🏃 Quick Start

```python
from plugin_runtime import Plugin, PluginRuntime

class EchoPlugin(Plugin):
    name = "echo"
    version = "1.0.0"

    def capabilities(self):
        return {"echo": lambda value: f"echo:{value}"}

runtime = PluginRuntime()
runtime.register(EchoPlugin())
runtime.boot_all()

print(runtime.invoke("echo", "echo", "hi"))
print(runtime.status_report())
```

### Dependencies & hooks

```python
class UpperPlugin(Plugin):
    name = "upper"
    depends_on = ("echo",)
    hooks_subscribed = ("request.received",)
    ...
```

## 🔧 Error Handling

```text
PluginError
├── DuplicatePluginError   # same name registered twice
├── UnknownPluginError     # invoke on unregistered/inactive plugin
└── DependencyCycleError   # circular depends_on chain
```

## 🧪 Testing

```bash
pytest tests/ -v
```

## 📝 Code Quality

- Full type hints (`X | None` style), frozen statuses
- Zero comments — names carry the meaning
- Boot/teardown ordering explicitly tested

## 📄 License

MIT — see [LICENSE](LICENSE).

## 👤 Author

**Kooroush Masoumi** - [kooroushmasoumi@gmail.com](mailto:kooroushmasoumi@gmail.com)

---

⭐ Star this repo if you find it useful!
