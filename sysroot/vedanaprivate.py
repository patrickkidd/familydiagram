import os.path
from pyqtdeploy import Component, PythonPackage


class VedanaPrivateComponent(Component):
    """ The vedanaprivate module component. """

    preinstalls = ['Python']
    provides = { 'vedanaprivate': PythonPackage() }

    def get_archive_name(self):
        return ''

    target_modules_dir = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

    def install(self):
        return
