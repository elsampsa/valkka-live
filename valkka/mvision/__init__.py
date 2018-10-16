# __all__=["movement"]

from valkka.mvision.base import *
from valkka.mvision.multiprocess import *

# add here your analyzers.  use try/except, so that if one module is broken, it does not affect the rest appearing in Valkka Live
try:
    from .import movement
except Exception as e:
    print("valkka.mvision.__init__ : could not import module movement : '"+str(e)+"'")

try: 
    from .import alpr
except Exception as e:
    print("valkka.mvision.__init__ : could not import module alpr : '"+str(e)+"'")
    
try:
    from .import nix
except Exception as e:
    print("valkka.mvision.__init__ : could not import module nix : '"+str(e)+"'")

try:
    from .import dflpr
except Exception as e:
    print("valkka.mvision.__init__ : could not import module dflpr : '"+str(e)+"'")
