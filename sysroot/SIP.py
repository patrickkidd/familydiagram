import glob
from pyqtdeploy.sysroot.plugins import SIP


class SIPComponent(SIP.SIPComponent):

    def get_archive(self):
        """Just use the lowercase module name for the archive name."""

        # Create the archive in the current directory.
        self.run(
            "sip-module",
            "--sdist",
            self.module_name,
            "--abi-version",
            str(self.abi_major_version),
        )

        # Work out what the name was.
        pattern = "{}-{}.*.tar.gz".format(
            self.module_name.lower().replace(".", "_"), self.abi_major_version
        )
        archives = glob.glob(pattern)

        if len(archives) == 0:
            self.error("sip-module didn't create an sdist")

        if len(archives) > 1:
            self.error("Several possible sdists found: " + ", ".join(archives))

        return archives[0]
