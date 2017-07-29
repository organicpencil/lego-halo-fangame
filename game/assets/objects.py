import bge
import utils


class Controllable:
    def __init__(self, owner):
        self.owner = owner

        # Default controls
        self.controls = c = {}
        c['forward'] = bge.events.WKEY
        c['back'] = bge.events.SKEY
        c['left'] = bge.events.AKEY
        c['right'] = bge.events.DKEY
        c['jump'] = bge.events.SPACEKEY
        c['interact'] = bge.events.EKEY
        c['shoot'] = bge.events.FKEY

        # Current input
        self.keystate = {}
        for k in list(c.keys()):
            self.keystate[k] = False

        self.freeMouse = False
        # Workaround for BGE's lousy input system
        self.ACCENTPRESSED = False

        # 0 = AI or None
        # 1 = Keyboard
        # 2+ = Controller ID - 2
        self.control_id = 0

    def set_keyboard_input(self):
        keystate = self.keystate
        held = utils.key_held

        for index, value in list(self.controls.items()):
            if held(value):
                keystate[index] = True
            else:
                keystate[index] = False

    def set_controller_input(self):
        if not self.control_id:
            ## TODO - Needs rework
            if bge.logic.joysticks[0] is not None:
                # Press start to join
                if 7 in bge.logic.joysticks[0].activeButtons:
                    self.using_controller = True
                    self.become_player()

                    old_ai = bge.logic.game.ai.getAIController(self)
                    squad = list(old_ai.squad)
                    if len(squad):
                        for s in squad:
                            s.setLeader(None)

                    bge.logic.game.ai.unregister(self)
                    new_ai = bge.logic.game.ai.register(self, self.team, 'AI_Stub')
                    for s in squad:
                        s.setLeader(new_ai)

                    # TEMP - remove hud PSA
                    scenes = bge.logic.getSceneList()
                    if len(scenes) == 2:
                        objects = scenes[1].objects
                        if 'PSA' in objects:
                            objects['PSA'].endObject()

            return

        controller_id = self.controlled - 2
        joystick = bge.logic.joysticks[controller_id]
        if joystick is not None:
            keystate = self.keystate

            yaw = joystick.axisValues[0]

            # Left
            if yaw < -0.2:
                keystate['left'] = True
            else:
                keystate['left'] = False

            # Right
            if yaw > 0.2:
                keystate['right'] = True
            else:
                keystate['right'] = False

            pitch = joystick.axisValues[1]  # Inverted

            # Forward
            if pitch < -0.2:
                keystate['forward'] = True
            else:
                keystate['forward'] = False

            # Back
            if pitch > 0.2:
                keystate['back'] = True
            else:
                keystate['back'] = False

            # Attack
            if joystick.axisValues[5] > -0.8:
                keystate['shoot'] = True
            else:
                keystate['shoot'] = False

            buttons = joystick.activeButtons

            # Jump
            if 0 in buttons:
                keystate['jump'] = True
            else:
                keystate['jump'] = False

            # Interact
            if 2 in buttons:
                keystate['interact'] = True
            else:
                keystate['interact'] = False

        else:
            # Unplugged.  Revert to AI
            self.become_ai()
            self.control_id = 0
            #bge.logic.game.ai.getAIController().setLeader('player')