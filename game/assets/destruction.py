import random
import bge


class Destroyed:
    def __init__(self, cont):
        self.owner = owner = cont.owner
        self.parts = []
        self.rebuild = 0

        for c in list(owner.children):
            self.parts.append(c)
            c['startPos'] = c.worldPosition.copy()
            c['startOri'] = c.worldOrientation.copy()
            c.removeParent()
            v = owner.getVectTo(c)[2]
            c.applyForce(v * (random.random() * 200.0), False)

        self.parts.sort(key=lambda x: x.worldPosition[2])

    def update(self):
        events = bge.logic.keyboard.events
        held = bge.logic.KX_INPUT_ACTIVE

        if events[bge.events.SPACEKEY] == held:
            parts = self.parts
            if len(parts) > self.rebuild:
                c = parts[self.rebuild]
                if c.parent is None:
                    c.setParent(self.owner)

                c.worldPosition = c.worldPosition.lerp(c['startPos'], 0.5)
                c.worldOrientation = c.worldOrientation.lerp(c['startOri'], 0.5)

                dist = c.getDistanceTo(c['startPos'])
                if dist < 0.1:
                    c.worldPosition = c['startPos']
                    c.worldOrientation = c['startOri']
                    self.rebuild += 1

            else:
                self.owner.scene.addObject('Warthog')
                self.owner.endObject()


def main(cont):
    owner = cont.owner
    d = owner.get('destroyed', None)
    if d is None:
        owner['destroyed'] = Destroyed(cont)
    else:
        d.update()