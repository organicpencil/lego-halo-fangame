import bge
from netplay import bitstring, component
import utils


class Controllable(component.GameObject):
    def start(self):
        self.keystate = bitstring.BitArray(bin='00000000')

        self.freeMouse = False
        # Workaround for BGE's lousy input system
        self.ACCENTPRESSED = False

    def set_keyboard_input(self):
        keystate = self.keystate

        held = utils.key_held

        if held(bge.events.WKEY):
            keystate.set(1, (0,))
        else:
            keystate.set(0, (0,))

        if held(bge.events.SKEY):
            keystate.set(1, (1,))
        else:
            keystate.set(0, (1,))

        if held(bge.events.AKEY):
            keystate.set(1, (2,))
        else:
            keystate.set(0, (2,))

        if held(bge.events.DKEY):
            keystate.set(1, (3,))
        else:
            keystate.set(0, (3,))

        if held(bge.events.SPACEKEY):
            keystate.set(1, (4,))
        else:
            keystate.set(0, (4,))

        if held(bge.events.EKEY):
            keystate.set(1, (5,))
        else:
            keystate.set(0, (5,))

        if held(bge.events.FKEY):
            keystate.set(1, (6,))
        else:
            keystate.set(0, (6,))

    def set_controller_input(self):
        if not self.controlled:
            if bge.logic.joysticks[0] is not None:
                # Press start to join
                if 7 in bge.logic.joysticks[0].activeButtons:
                    self.setPlayer(2)

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
                keystate.set(1, (2,))
            else:
                keystate.set(0, (2,))

            # Right
            if yaw > 0.2:
                keystate.set(1, (3,))
            else:
                keystate.set(0, (3,))

            pitch = joystick.axisValues[1]  # Inverted

            # Forward
            if pitch < -0.2:
                keystate.set(1, (0,))
            else:
                keystate.set(0, (0,))

            # Back
            if pitch > 0.2:
                keystate.set(1, (1,))
            else:
                keystate.set(0, (1,))

            # Attack
            if joystick.axisValues[5] > -0.8:
                keystate.set(1, (6,))
            else:
                keystate.set(0, (6,))

            buttons = joystick.activeButtons

            # Jump
            if 0 in buttons:
                keystate.set(1, (4,))
            else:
                keystate.set(0, (4,))

            # Interact
            if 2 in buttons:
                keystate.set(1, (5,))
            else:
                keystate.set(0, (5,))

        else:
            # Unplugged.  Revert to AI
            # There's no hotplugging in 2.78 so we can't actually detect this
            # Here's the code anyway
            self.controlled = 0

            old_ai = bge.logic.game.ai.getAIController(self)
            squad = list(old_ai.squad)
            if len(squad):
                for s in squad:
                    s.setLeader(None)

            bge.logic.game.ai.unregister(self)
            new_ai = bge.logic.game.ai.register(self, self.team, 'AI_Standard')
            for s in squad:
                s.setLeader(new_ai)

            new_ai.setLeader(bge.logic.game.ai.getAIController(bge.logic.players[0]))

            del self.owner['player']