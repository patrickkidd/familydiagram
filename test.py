import sys, logging
from PyQt5.QtCore import *
from PyQt5.QtGui import *



def one():
    from .pkdiagram import debug


logging.basicConfig(stream=sys.stdout, format="%(filename)s:%(lineno)s %(message)s")

log = logging.getLogger(__name__)

log.setLevel(logging.INFO)
o1, c1 = QObject(), QColor()
log.info(f"here, {o1}, {c1}")


bleh = Debug()
