from core import Component


class HUD(Component):
    def __init__(self, owner):
        Component.__init__(self, owner)
        self.subscribe_to_event('score')

    def handle_event_score(self, data):
        player = data[0]
        score = data[1]
        stud = data[2]

        # Update text
        hud = self.owner.scene
        hud.objects['p{}_studs'.format(player)]['Text'] = score

        # Play pickup animation
        scene = stud.scene
        # FIXME - fake stud is being created at center of screen
        # Needs to appear at same position and rotation relative to the camera
        pos = scene.active_camera.getVectTo(stud.worldPosition)[2]
        pos = pos * hud.active_camera.worldOrientation.inverted()
        obj = stud.name.split('-dynamic')[0]
        studcolor = hud.objects['p{}_studcolor'.format(player)]
        studcolor.replaceMesh(obj)
        fake = hud.addObject(obj + '-fake')
        fake.worldPosition = pos
        fake['p'] = studcolor
        fake.scaling = (0.4, 0.4, 0.4)


def register(cont):
    owner = cont.owner
    if not 'component' in owner:
        owner['component'] = HUD(owner)
