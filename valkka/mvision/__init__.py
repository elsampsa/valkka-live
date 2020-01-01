# __all__=["movement"]

from valkka.mvision.base import *
from valkka.mvision.multiprocess import *

# add here your analyzers.  use try/except, so that if one module is broken, it does not affect the rest
try:
    from .import movement
except Exception as e:
    print("valkka.mvision.__init__ : could not import module movement : '"+str(e)+"'")

"""
try: 
    from .import alpr
except Exception as e:
    print("valkka.mvision.__init__ : could not import module alpr : '"+str(e)+"'")
"""

try:
    from .import nix
except Exception as e:
    print("valkka.mvision.__init__ : could not import module nix : '"+str(e)+"'")

try:
    from .import yolo3
except Exception as e:
    print("valkka.mvision.__init__ : could not import module yolo3 : '"+str(e)+"'")

try:
    from .import yolo2
except Exception as e:
    print("valkka.mvision.__init__ : could not import module yolo2 : '"+str(e)+"'")

try:
    from .import yolo3tiny
except Exception as e:
    print("valkka.mvision.__init__ : could not import module yolo3tiny : '"+str(e)+"'")

try:
    from .import yolo3client
except Exception as e:
    print("valkka.mvision.__init__ : could not import module yolo3client : '"+str(e)+"'")

try:
    from .import yolo3master
except Exception as e:
    print("valkka.mvision.__init__ : could not import module yolo3master : '"+str(e)+"'")
