import os
import toml
from pyqtdeploy.sysroot.plugins import PyQt
from pyqtdeploy import ComponentOption


class PyQtComponent(PyQt.PyQtComponent):

    def get_options(self):
        options = super().get_options()

        options.append(
            ComponentOption(
                "extra_compile_args",
                type=list,
                help="Pass these on to each module in pyproject.toml.",
            )
        )

        return options

    def run(self, *args, capture=False):
        """Add multiprocessing to make."""

        _args = tuple(args)
        if args[0] == "sip-install":
            # Add extra options to pyproject.toml before it's run.
            pyproject = toml.load("pyproject.toml")
            bindings_section = self._get_section("tool.sip.bindings", pyproject)
            for module in bindings_section.values():
                if isinstance(module, dict):
                    module.update({"extra-compile-args": self.extra_compile_args})
            with open("pyproject.toml", "w") as f:
                toml.dump(pyproject, f)

        return super().run(*_args, capture=capture)
