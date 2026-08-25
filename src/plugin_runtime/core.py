from __future__ import annotations

import time
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar


class PluginError(Exception):
    pass


class DuplicatePluginError(PluginError):
    def __init__(self, name: str) -> None:
        super().__init__(f"plugin already registered: {name!r}")


class UnknownPluginError(PluginError):
    def __init__(self, name: str) -> None:
        super().__init__(f"unknown plugin: {name!r}")


class DependencyCycleError(PluginError):
    pass


class HookRegistry:
    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable[[dict[str, Any]], Any]]] = {}

    def register(self, hook_name: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        self._hooks.setdefault(hook_name, []).append(callback)

    def emit(self, hook_name: str, context: dict[str, Any]) -> list[Any]:
        return [callback(context) for callback in self._hooks.get(hook_name, [])]

    def hook_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._hooks))


@dataclass
class PluginContext:
    config: dict[str, Any] = field(default_factory=dict)
    services: dict[str, Any] = field(default_factory=dict)
    hooks: HookRegistry = field(default_factory=HookRegistry)

    def service(self, name: str) -> Any:
        if name not in self.services:
            raise PluginError(f"service not provided: {name!r}")
        return self.services[name]


class Plugin:
    name: ClassVar[str] = ""
    version: ClassVar[str] = "0.0.0"
    depends_on: ClassVar[tuple[str, ...]] = ()
    hooks_subscribed: ClassVar[tuple[str, ...]] = ()

    def setup(self, context: PluginContext) -> None: ...
    def teardown(self, context: PluginContext) -> None: ...

    @abstractmethod
    def capabilities(self) -> dict[str, Callable[[Any], Any]]:
        raise NotImplementedError

    def on_hook(self, hook_name: str, context: dict[str, Any]) -> Any:
        return None


@dataclass(frozen=True)
class PluginStatus:
    name: str
    version: str
    state: str
    setup_seconds: float


class PluginRuntime:
    def __init__(self, base_context: PluginContext | None = None) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._states: dict[str, str] = {}
        self._setup_times: dict[str, float] = {}
        self.context = base_context or PluginContext()

    def register(self, plugin: Plugin) -> "PluginRuntime":
        if plugin.name in self._plugins:
            raise DuplicatePluginError(plugin.name)
        self._validate_dependencies(plugin.name, plugin.depends_on)
        self._plugins[plugin.name] = plugin
        self._states[plugin.name] = "registered"
        return self

    def _validate_dependencies(self, name: str,
                               dependencies: tuple[str, ...], seen: frozenset[str] = frozenset()) -> None:
        if name in seen:
            raise DependencyCycleError(f"circular dependency through {name!r}")
        for dependency in dependencies:
            existing = self._plugins.get(dependency)
            if existing is None:
                continue
            self._validate_dependencies(dependency, existing.depends_on, seen | {name})

    def startup_order(self) -> list[str]:
        order: list[str] = []
        visited: set[str] = set()
        temp: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in temp:
                raise DependencyCycleError(f"circular dependency at {name!r}")
            temp.add(name)
            for dependency in self._plugins[name].depends_on:
                if dependency in self._plugins:
                    visit(dependency)
            temp.discard(name)
            visited.add(name)
            order.append(name)

        for plugin_name in sorted(self._plugins):
            visit(plugin_name)
        return order

    def boot_all(self) -> None:
        for name in self.startup_order():
            self.boot_plugin(name)

    def boot_plugin(self, name: str) -> PluginStatus:
        plugin = self._get_started_candidate(name)
        started = time.perf_counter()
        plugin.setup(self.context)
        duration = time.perf_counter() - started
        self._setup_times[name] = duration
        self._states[name] = "active"
        for hook in plugin.hooks_subscribed:
            self.context.hooks.register(hook, plugin.on_hook)
        return PluginStatus(name=name, version=plugin.version,
                            state="active", setup_seconds=round(duration, 4))

    def shutdown_all(self) -> None:
        for name in reversed(self.startup_order()):
            if self._states.get(name) == "active":
                self._plugins[name].teardown(self.context)
                self._states[name] = "stopped"

    def invoke(self, plugin_name: str, capability: str, argument: Any) -> Any:
        plugin = self._plugins.get(plugin_name)
        if plugin is None or self._states.get(plugin_name) != "active":
            raise UnknownPluginError(plugin_name)
        capabilities = plugin.capabilities()
        if capability not in capabilities:
            raise PluginError(
                f"{plugin_name!r} has no capability {capability!r}; "
                f"available: {sorted(capabilities)}"
            )
        return capabilities[capability](argument)

    def status_report(self) -> list[PluginStatus]:
        report = []
        for name, plugin in self._plugins.items():
            report.append(PluginStatus(
                name=name,
                version=plugin.version,
                state=self._states.get(name, "registered"),
                setup_seconds=round(self._setup_times.get(name, 0.0), 4),
            ))
        return report

    def _get_started_candidate(self, name: str) -> Plugin:
        plugin = self._plugins.get(name)
        if plugin is None:
            raise UnknownPluginError(name)
        return plugin
