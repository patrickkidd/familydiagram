import os.path
import re

from pyqtdeploy.sysroot.plugins.wheel import wheelPlugin


class fdwheelPlugin(wheelPlugin):

    def get_archive_name(self):
        """Return the filename of the wheel."""

        source_dir = self._sysroot.source_dirs[0]
        wheel_fpath = os.path.join(source_dir, self.wheel)
        if not os.path.exists(wheel_fpath):
            parts = self._wheel_parts()
            version = parts["version"]
            cmd = f"pip download --dest {source_dir} {self.name}=={version}"
            print(cmd)
            retval = os.system(cmd)
            if retval != 0:
                raise ValueError(
                    f"Could not use pip to download: {self.name}=={version}"
                )

        return wheel_fpath

    def _wheel_parts(self) -> dict:
        wheel_file_re = re.compile(
            r"^(?P<name>.+?)-(?P<version>.+?)(?:-(?P<build_tag>.+?))?-(?P<python_tag>.+?)-(?P<abi_tag>.+?)-(?P<platform_tag>.+?)\.whl$"
        )
        match = wheel_file_re.match(self.wheel)
        if not match:
            raise ValueError(f"Invalid wheel filename: {self.wheel}")
        params = match.groupdict()
        return params

    def get_archive_urls(self):
        """Return the list of URLs where the source archive might be
        downloaded from.
        """

        def wheel_url(name, version, build_tag, python_tag, abi_tag, platform_tag):
            host = "https://files.pythonhosted.org"
            optional_build_tag = f"-{build_tag}" if build_tag else ""
            filename = f"{name}-{version}{optional_build_tag}-{python_tag}-{abi_tag}-{platform_tag}.whl"
            return f"{host}/packages/{python_tag}/{name[0]}/{name}/{filename}"

        return [wheel_url(**params)]

    def install(self):
        """Install for the target."""

        self.unpack_wheel(self.get_archive())

    def verify(self):
        """Verify the component."""

        wheel_version = self.parse_version_number(self.wheel.split("-")[1])

        if self.version is None:
            self.version = wheel_version
        elif self.version != wheel_version:
            self.error(
                "v{0} is specified but the wheel is v{1}".format(
                    self.version, wheel_version
                )
            )
