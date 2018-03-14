import logging
import bge
import mathutils
from . import Component


class FollowCam(Component):
    def __init__(self, owner):
        Component.__init__(self, owner)
        self.start = owner.worldPosition.copy()
        self.target = self.start.copy()

        self.navmesh = owner.scene.objects.get('navmesh-camera', None)
        if self.navmesh is None:
            logging.warning('Camera navmesh not found. Add a navigation mesh ~13 units off the ground and name it "navmesh-camera".')

    def update(self):
        cam = self.owner
        pos = mathutils.Vector()
        i = 0

        # Center view between all players
        for p in bge.logic.core.players:
            if p is not None:
                component = p.component
                if component is not None:
                    ob = component.owner
                    if not ob.invalid:
                        pos += ob.worldPosition
                        i += 1

        if i == 0:
            # No players exist
            return

        pos = pos / i
        #"""

        #v = cam.getVectTo(ob)[1]
        v = cam.getVectTo(pos)[1]
        cam.alignAxisToVect(-v, 2, 0.1)
        ori = cam.worldOrientation.to_euler()
        if ori[0] < 0.0:
            ori[2] += 3.14
        ori[1] = 0.0
        cam.worldOrientation = ori
        #cam.alignAxisToVect((1, 0, 0), 0)

        # Determine new target position
        pos[2] = cam.worldPosition[2]
        nav = self.navmesh
        if nav is not None:
            path = nav.findPath(self.start, pos)
            #print(path)
            k = 1
            for i in range(0, len(path)):
                # Find point along path that is xx distance from the player
                if len(path) > k:
                    p0 = path[i]
                    p1 = path[k]
                    d1 = (p1 - pos).length
                    if d1 > 30.0:
                        # Too far, next
                        i += 1
                        k += 1
                    else:
                        # Somewhere between these two points
                        #d0 = p.getDistanceTo(p0)
                        delta = 30.0 - d1  # How far back along the path to go
                        # Don't exceed path delta, else go through walls
                        pathdelta = (p1 - p0).length
                        if delta > pathdelta:
                            delta = pathdelta

                        vec = p1 - p0
                        vec.normalize()
                        vec.negate()
                        self.target = p1 + (vec * delta)
                        break

        cam.worldPosition = cam.worldPosition.lerp(self.target, 0.02)
        #print (cam.getDistanceTo(pos))


def register(cont):
    owner = cont.owner
    if not 'component' in owner:
        owner['component'] = FollowCam(owner)
