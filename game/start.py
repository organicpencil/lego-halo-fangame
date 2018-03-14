import bge
from core import Core


def main(cont):
    c = cont.owner.get('core', None)
    if c is None:
        bge.logic.core = cont.owner['core'] = Core()
    else:
        c.update()
