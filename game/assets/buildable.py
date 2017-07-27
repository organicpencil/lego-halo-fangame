import random


class Buildable:
    def __init__(self, cont):
        self.owner = owner = cont.owner
        self.parts = []
        self.rebuild = 0
        self.build = False

        for c in list(owner.children):
            self.parts.append(c)
            c['startPos'] = c.worldPosition.copy()
            c['startOri'] = c.worldOrientation.copy()
            c.removeParent()
            v = owner.getVectTo(c)[2]
            c.applyForce(v * (random.random() * 200.0), False)

        self.parts.sort(key=lambda x: x.worldPosition[2])

    def update(self):
        owner = self.owner
        group = owner.groupObject

        triggered = False
        if group is not None:
            triggered = group.get('build', False)

        if triggered or self.build:
            self.build = False
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
                owner.scene.addObject(owner['object'])
                owner.endObject()


def main(cont):
    owner = cont.owner
    b = owner.get('buildable', None)
    if b is None:
        owner['buildable'] = Buildable(cont)
    else:
        b.update()