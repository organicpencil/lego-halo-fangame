import bge
import mathutils
import utils
STUDS = ['stud-silver', 'stud-gold', 'stud-blue', 'stud-purple', 'stud-shinypurple']
SCORES = [10, 100, 1000, 10000, 100000]


def fake(cont):
    owner = cont.owner
    p = bge.logic.getCurrentScene().objects['p' + owner['p'] + '_studcolor']
    owner.worldPosition = owner.worldPosition.lerp(p.worldPosition, 0.05)
    if owner.getDistanceTo(p) < 0.1:
        owner.endObject()