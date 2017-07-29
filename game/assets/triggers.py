import bge


def button(cont):
    owner = cont.owner
    if cont.sensors['Collision'].positive:
        owner.groupObject['button'] = True
        owner.color = [0, 1, 0, 1]

        arm = owner.parent
        if arm.isPlayingAction():
            frame = arm.getActionFrame()
        else:
            frame = 0

        arm.playAction('button-armatureAction', frame, 5)

        buttonset = owner.groupObject.get('set', None)
        if not owner['player_standing']:
            other = cont.sensors['Collision'].hitObject
            if '_component' in other:
                if other['_component'] is bge.logic.players[0]:
                    owner['player_standing'] = True
                    objects = bge.logic.getCurrentScene().objects
                    squad = list(bge.logic.game.ai.getAIController(bge.logic.players[0]).squad)
                    for ob in objects:
                        if ob.name == 'button' and ob is not owner:
                            if ob.groupObject.get('set', None) == buttonset:
                                if not ob.groupObject['button']:
                                    if len(squad):
                                        ai = squad.pop()
                                        ai.go_to_button(ob)

    else:
        owner.groupObject['button'] = False
        owner.color = [1, 0, 0, 1]

        arm = owner.parent
        if arm.isPlayingAction():
            frame = arm.getActionFrame()
        else:
            frame = 5

        arm.playAction('button-armatureAction', frame, 0)

        if owner['player_standing']:
            owner['player_standing'] = False
            for ai in bge.logic.game.ai.getAIController(bge.logic.players[0]).squad:
                ai.forget_location()