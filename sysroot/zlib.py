import os
import shutil

from pyqtdeploy.sysroot.plugins import zlib


class zlibComponent(zlib.zlibComponent):

    def install(self):
        if self.target_platform_name == "ios" and self.install_from_source:
            self._install_ios_universal()
        else:
            super().install()

    def _install_ios_universal(self):
        self.unpack_archive(self.get_archive())

        lib_arm64 = os.path.join(self.sysroot_dir, 'lib', 'libz-arm64.a')
        lib_x86_64 = os.path.join(self.sysroot_dir, 'lib', 'libz-x86_64.a')
        lib_universal = os.path.join(self.sysroot_dir, 'lib', 'libz.a')

        simulator_sdk = self.run('xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path', capture=True).strip()

        self.progress("Building for arm64 (device)")
        os.environ['CFLAGS'] = f"-fembed-bitcode -O3 -arch arm64 -isysroot {self.apple_sdk}"
        os.environ['CHOST'] = "arm-apple-darwin"
        self.run('./configure', '--static', f'--prefix={self.sysroot_dir}')
        self.run(self.host_make)
        shutil.copy('libz.a', lib_arm64)
        self.run(self.host_make, 'clean')

        self.progress("Building for x86_64 (simulator)")
        os.environ['CFLAGS'] = f"-fembed-bitcode -O3 -arch x86_64 -isysroot {simulator_sdk}"
        os.environ['CHOST'] = "x86_64-apple-darwin"
        self.run('./configure', '--static', f'--prefix={self.sysroot_dir}')
        self.run(self.host_make)
        shutil.copy('libz.a', lib_x86_64)

        self.run(self.host_make, 'install')

        del os.environ['CFLAGS']
        del os.environ['CHOST']

        self.progress("Creating universal binary (arm64 + x86_64)")
        self.run('lipo', '-create', lib_arm64, lib_x86_64, '-output', lib_universal)

        os.remove(lib_arm64)
        os.remove(lib_x86_64)
