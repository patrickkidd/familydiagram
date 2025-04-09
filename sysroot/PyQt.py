import os
from pyqtdeploy.sysroot.plugins import PyQt


class PyQtComponent(PyQt.PyQtComponent):

    def run(self, *args, capture=False):
        """Add multiprocessing to make."""
        qt = self.get_component("Qt")

        _args = tuple(args)
        if args[0] == self.host_make:
            self.verbose("Adding args for concurrent build.")
            if os.name == "nt":
                os.environ["CL"] = "/MP"
            else:
                _args += ("-j16",)
        elif args[0] == qt.host_qmake and self.target_arch_name == "ios-64":
            _args += ("QMAKE_CFLAGS=-Wno-deprecated-declarations",)
        #     self.verbose('*********** Adding args for debug build.')
        #     _args += ('CONFIG+=debug', 'QMAKE_CFLAGS=-g')
        return super().run(*_args, capture=capture)
