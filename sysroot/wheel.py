import json
import os
import zipfile
from pathlib import Path
from urllib.request import urlopen

from pyqtdeploy import Component, ComponentOption, PythonModule, PythonPackage


class wheelPlugin(Component):
    preinstalls = ["Python"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._provides_cache = None
        # Log that our custom plugin is being used
        import sys
        print(f"[CUSTOM WHEEL PLUGIN] Loaded for component '{args[0] if args else '?'}' from {__file__}", file=sys.stderr)

    @property
    def provides(self):
        if self._provides_cache is not None:
            return self._provides_cache

        dependencies = getattr(self, 'dependencies', None) or []
        exclusions = getattr(self, 'exclusions', None) or []

        # Try to analyze wheel contents to determine what modules it provides
        try:
            archive_path = self.get_archive()
            if archive_path and os.path.exists(archive_path):
                modules = self._analyze_wheel_contents(archive_path, dependencies, exclusions)
                if modules:
                    self.verbose(f"wheel '{self.name}' provides: {', '.join(sorted(modules.keys()))}")
                    self._provides_cache = modules
                    return modules
        except Exception:
            pass

        # CRITICAL: During build phase, get_archive() may not be available
        # For single-module wheels like six, we need to declare them as PythonModule
        # based on the wheel filename pattern, not archive inspection

        # Check if this is a known single-module wheel based on naming conventions
        # Wheels like "six-X.Y.Z-py2.py3-none-any.whl" contain a single six.py file
        wheel_name = getattr(self, 'wheel', '')
        if wheel_name.startswith('six-'):
            # six.py is a single module
            self._provides_cache = {
                'six': PythonModule(version=self.version, deps=dependencies)
            }
            return self._provides_cache

        # Default fallback: assume wheel provides a package matching component name
        default_provides = {
            self.name: PythonPackage(
                version=self.version,
                deps=dependencies,
                exclusions=exclusions
            )
        }
        self._provides_cache = default_provides
        return default_provides

    def _analyze_wheel_contents(self, archive_path, dependencies, exclusions):
        modules = {}

        with zipfile.ZipFile(archive_path, 'r') as whl:
            top_level_items = set()

            for name in whl.namelist():
                # Skip files in root (no path separator)
                if '/' not in name and '\\' not in name:
                    continue

                parts = Path(name).parts
                if len(parts) == 0:
                    continue

                first_part = parts[0]

                # Skip metadata directories
                if first_part.endswith(('.dist-info', '.egg-info', '__pycache__')):
                    continue

                # Single .py file at root = module (like six.py)
                if first_part.endswith('.py') and len(parts) == 1:
                    module_name = first_part[:-3]
                    if module_name != '__init__':
                        top_level_items.add(('module', module_name))
                # Directory at root = package (like dateutil/)
                elif not first_part.endswith('.py'):
                    top_level_items.add(('package', first_part))

            for item_type, item_name in top_level_items:
                if item_type == 'module':
                    modules[item_name] = PythonModule(
                        version=self.version,
                        deps=dependencies
                    )
                else:
                    modules[item_name] = PythonPackage(
                        version=self.version,
                        deps=dependencies,
                        exclusions=exclusions
                    )

        return modules

    version_is_optional = True

    def get_archive_name(self):
        return self.wheel

    def get_archive_urls(self):
        # Uses PyPI JSON API instead of HTML scraping
        api_url = f"https://pypi.org/pypi/{self.project}/{self.version}/json"

        self.verbose(f"fetching wheel info from {api_url}")

        try:
            with urlopen(api_url) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as e:
            self.verbose(f"unable to fetch PyPI JSON API: {e}")
            return []

        wheel_filename = self.get_archive_name()

        for url_info in data.get("urls", []):
            if url_info.get("filename") == wheel_filename:
                wheel_url = url_info.get("url", "")
                if wheel_url:
                    self.verbose(f"found wheel URL: {wheel_url}")
                    return [wheel_url[: -len(wheel_filename)]]

        self.verbose(f"wheel '{wheel_filename}' not found in PyPI JSON response")
        return []

    def get_options(self):
        options = super().get_options()

        options.append(
            ComponentOption(
                "dependencies",
                type=list,
                help="The component:modules that this component " "depends on.",
            )
        )

        options.append(
            ComponentOption(
                "exclusions",
                type=list,
                help="The files and directories of this component "
                "that should be excluded.",
            )
        )

        options.append(
            ComponentOption(
                "project",
                type=str,
                default=self.name,
                help="The name of the PyPI project.",
            )
        )

        options.append(
            ComponentOption(
                "wheel", type=str, required=True, help="The name of the wheel."
            )
        )

        return options

    def install(self):
        self.unpack_wheel(self.get_archive())

    def verify(self):
        wheel_version = self.parse_version_number(self.wheel.split("-")[1])

        if self.version is None:
            self.version = wheel_version
        elif self.version != wheel_version:
            self.error(
                "v{0} is specified but the wheel is v{1}".format(
                    self.version, wheel_version
                )
            )
