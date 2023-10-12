from sipbuild import Option, Project, PyProjectOptionException
import pyqtbuild


class PKDiagramProject(pyqtbuild.PyQtProject):
    """ A project that adds an additional configuration option and introspects
    the system to determine its value.
    """

    def get_options(self):
        """ Return the sequence of configurable options. """

        # Get the standard options.
        options = super().get_options()

        # Add our new option.
        options.append(Option('sources'))

        return options

    def apply_nonuser_defaults(self, tool):
        """ Apply any non-user defaults. """

        if self.sources is None:
            pass
            # The option wasn't specified in pyproject.toml so we introspect
            # the system.

            # from sys import platform

            # if platform == 'linux':
            #     self.sources = [ "unsafearea.cpp", "_pkdiagram.cpp", "_pkdiagram_win32.cpp" ]
            # elif platform == 'darwin':
            #     self.sources = [ "unsafearea.cpp", "_pkdiagram.cpp", "_pkdiagram_mac.mm" ]
            # elif platform == 'win32':
            #     self.sources = [ "unsafearea.cpp", "_pkdiagram.cpp", "_pkdiagram_win32.cpp" ]
            # else:
            #     raise PyProjectOptionException('platform',
            #             "the '{0}' platform is not supported".format(platform))
        else:
            # The option was set in pyproject.toml so we just verify the value.
            if self.platform not in ('Linux', 'macOS', 'Windows'):
                raise PyProjectOptionException('platform',
                        "'{0}' is not a valid platform".format(self.platform))

        # Apply the defaults for the standard options.
        super().apply_nonuser_defaults(tool)

    def update(self, tool):
        """ Update the project configuration. """

        import sys

        # Get the 'core' bindings and add the platform to the list of tags.
        _pkdiagram_bindings = self.bindings['_pkdiagram']
        from sys import platform
        libraries = []
        if platform == 'linux':
            sources = [ "_pkdiagram_win32.cpp" ]
        elif platform == 'darwin':
            sources = [ "_pkdiagram_mac.mm" ]
        elif platform == 'win32':
            sources = [ "_pkdiagram_win32.cpp" ]
            libraries = [ "shlwapi" ]
        else:
            raise PyProjectOptionException('platform',
                    "the '{0}' platform is not supported".format(platform))
        _pkdiagram_bindings.sources += sources
        _pkdiagram_bindings.libraries += libraries

