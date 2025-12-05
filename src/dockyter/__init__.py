from .magics import Dockyter

def load_ipython_extension(ipython):
    ipython.register_magics(Dockyter)
