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
