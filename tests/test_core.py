import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from plugin_runtime import (
    DependencyCycleError,
    DuplicatePluginError,
    Plugin,
    PluginContext,
    PluginRuntime,
    UnknownPluginError,
)


class EchoPlugin(Plugin):
    name = "echo"
    version = "1.0.0"

    def capabilities(self):
        return {"echo": lambda value: f"echo:{value}"}


class UpperPlugin(EchoPlugin):
    name = "upper"
    depends_on = ("echo",)

    def capabilities(self):
        return {"upper": lambda value: str(value).upper()}


def test_register_and_invoke_capability():
    runtime = PluginRuntime()
    runtime.register(EchoPlugin()).boot_all()
    assert runtime.invoke("echo", "echo", "hi") == "echo:hi"


def test_duplicate_registration_rejected():
    runtime = PluginRuntime()
    runtime.register(EchoPlugin())
    with pytest.raises(DuplicatePluginError):
        runtime.register(EchoPlugin())


def test_unknown_plugin_rejected():
    with pytest.raises(UnknownPluginError):
        PluginRuntime().invoke("ghost", "cap", None)


def test_unknown_capability_lists_available():
    runtime = PluginRuntime()
    runtime.register(EchoPlugin()).boot_all()
    with pytest.raises(Exception, match="available"):
        runtime.invoke("echo", "shout", "x")


def test_inactive_plugin_cannot_be_invoked():
    runtime = PluginRuntime()
    runtime.register(EchoPlugin())
    with pytest.raises(UnknownPluginError):
        runtime.invoke("echo", "echo", "x")


def test_startup_order_respects_dependencies():
    runtime = PluginRuntime()
    runtime.register(UpperPlugin())
    runtime.register(EchoPlugin())
    order = runtime.startup_order()
    assert order.index("echo") < order.index("upper")


def test_direct_cycle_detected():
    class A(Plugin):
        name = "a"
        depends_on = ("b",)
        def capabilities(self): return {}

    class B(Plugin):
        name = "b"
        depends_on = ("a",)
        def capabilities(self): return {}

    runtime = PluginRuntime()
    runtime.register(A())
    runtime.register(B())
    with pytest.raises(DependencyCycleError):
        runtime.startup_order()


def test_missing_dependency_is_tolerated_at_register():
    runtime = PluginRuntime()
    runtime.register(UpperPlugin())
    runtime.boot_all()
    assert runtime._states["upper"] == "active"


def test_hooks_fire_through_context():
    seen = []

    class Hooked(Plugin):
        name = "hooked"
        hooks_subscribed = ("request.received",)

        def on_hook(self, context, hook_name=None):
            seen.append(context["path"])
            return None

        def capabilities(self):
            return {}

    runtime = PluginRuntime()
    runtime.register(Hooked())
    runtime.boot_all()
    runtime.context.hooks.emit("request.received", {"path": "/x"})
    assert seen == ["/x"]


def test_teardown_runs_reverse_order():
    torn_down = []

    class T1(Plugin):
        name = "t1"
        def teardown(self, context): torn_down.append("t1")
