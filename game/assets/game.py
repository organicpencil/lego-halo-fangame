import os
import sys
import bge
import ai


def exception_handler(type_, value, tb):
    # print the exception
    import traceback
    traceback.print_exception(type_, value, tb)

    # start the python debugger
    # (remove these two lines if you don't want to use pdb)
    #import pdb
    #pdb.pm()

    # stop the game engine after you finish with pdb
    bge.logic.endGame()

# tell Python to use your function
sys.excepthook = exception_handler


def load_assets():
    # First release any assets in case we changed scene
    while len(bge.logic.LibList()):
        bge.logic.LibFree(bge.logic.LibList[0])

    path = bge.logic.expandPath('//assets/libload/')
    try:
        files = os.listdir(path)
    except:
        path = bge.logic.expandPath('//../assets/libload/')
        files = os.listdir(path)

    for f in files:
        if f.endswith(".blend"):
            bge.logic.LibLoad(path + f, 'Scene', load_actions=True)


class Game:
    def __init__(self):
        self.timers = []
        self.last_time = bge.logic.getFrameTime()
        self.ai = ai.AIManager()

        # Workaround for delayed scene add
        self.init_hud = True
        self.deltatime = 1.0 / 60.0

    def add_timer(self, seconds, callback, args):
        self.timers.append(Timer(seconds, callback, args))

    def add_lerper(self, ob, destination, factor):
        self.timers.append(Lerper(ob, destination, factor))

    def refresh_hud(self):
        try:
            hud = bge.logic.getSceneList()[1]
        except:
            # Must wait 1 frame for overlay scenes to initiate
            return

        self.init_hud = False

        # Player 1
        player = bge.logic.players[0]

        if player is not None:
            # Icon
            icon = hud.objects['p1_icon']
            if not len(icon.children):
                icon.color = [0, 1, 0, 1]
                ic = hud.addObject(hud.objectsInactive[player.icon], icon)
                ic.worldPosition[1] -= 0.1
                ic.setParent(icon)

            # Hearts
            hearts = hud.objects['p1_hearts']
            for c in list(hearts.children):
                c.endObject()

            for i in range(player.hp):
                ob = hud.addObject(hud.objectsInactive['icon-heart'], hearts)
                ob.setParent(hearts)
                ob.worldPosition[0] += i * 0.32

                if i + 1 == player.hp:
                    # Last heart is animated
                    ob.state = 2

            # Shield
            if player.shield is not None:
                for i in range(player.shield):
                    ob = hud.addObject(hud.objectsInactive['shield'], hearts)
                    ob.setParent(hearts)
                    ob.worldPosition[0] += i * 0.22
                    ob.worldPosition[2] -= 0.3

        # Player 2
        player = bge.logic.players[1]

        if player is not None:
            # Icon
            icon = hud.objects['p2_icon']
            if not len(icon.children):
                icon.color = [0, 0, 1, 1]
                ic = hud.addObject(hud.objectsInactive[player.icon], icon)
                ic.worldPosition[1] -= 0.1
                ic.setParent(icon)

            # Hearts
            hearts = hud.objects['p2_hearts']
            for c in list(hearts.children):
                c.endObject()

            for i in range(player.hp):
                ob = hud.addObject(hud.objectsInactive['icon-heart'], hearts)
                ob.setParent(hearts)
                ob.worldPosition[0] -= i * 0.32

                if i + 1 == player.hp:
                    # Last heart is animated
                    ob.state = 2

            # Shield
            if player.shield is not None:
                for i in range(player.shield):
                    ob = hud.addObject(hud.objectsInactive['shield'], hearts)
                    ob.setParent(hearts)
                    ob.worldPosition[0] -= i * 0.22
                    ob.worldPosition[2] -= 0.3

            # Icon
            icon = hud.objects['p1_icon']
            for c in list(icon.children):
                c.endObject()
            ic = hud.addObject(hud.objectsInactive[player.icon], icon)
            ic.setParent(icon)

        # TODO - Split this up rather than refreshing everything
        # Also duplicate code wtf

    def update(self):
        now = bge.logic.getFrameTime()
        self.deltatime = dt = min(now - self.last_time, 0.1)  # Things start slowing down < 10 fps
        self.last_time = now

        # Workaround for delayed scene add
        if self.init_hud:
            self.refresh_hud()

        self.ai.update(dt)

        for b in list(self.timers):
            if b.update(dt):
                self.timers.remove(b)


class Timer:
    def __init__(self, seconds, callback, args):
        self.seconds = seconds
        self.callback = callback
        self.args = args

    def update(self, dt):
        self.seconds -= dt
        if self.seconds < 0.0:
            self.callback(self.args)
            return True

        return False


class Lerper:
    def __init__(self, ob, destination, factor):
        self.ob = ob
        self.destination = destination
        self.factor = factor

        # Limit to 60 frames
        self.frames = 60

    def update(self, dt):
        if type(self.destination) == bge.types.KX_GameObject:
            if self.destination.invalid:
                return True

            dest = self.destination.worldPosition
        else:
            dest = self.destination

        ob = self.ob
        if ob.invalid:
            return True
        ob.worldPosition = ob.worldPosition.lerp(dest, self.factor)

        if ob.getDistanceTo(dest) < 0.1:
            ob.worldPosition = dest
            return True

        self.frames -= 1
        if self.frames < 1:
            return True

        return False


def main():
    if hasattr(bge.logic, 'game'):
        bge.logic.game.update()
    else:
        # First frame
        load_assets()

        bge.logic.players = [None, None]
        bge.logic.game = Game()