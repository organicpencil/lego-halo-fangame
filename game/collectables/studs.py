import bge
import mathutils


def fake(cont):
    owner = cont.owner
    p = owner['p']
    owner.worldPosition = owner.worldPosition.lerp(p.worldPosition, 0.05)
    if owner.getDistanceTo(p) < 0.1:
        owner.endObject()


def register(cont):
    owner = cont.owner
    if not 'init' in owner:
        owner['init'] = 1
        bge.logic.core.studs.append(owner)
