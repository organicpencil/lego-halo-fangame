import bge


def button(cont):
    owner = cont.owner
    group = owner.groupObject
    if cont.sensors['Collision'].positive:
        if group['button']:
            return

        group['button'] = True
        owner.color = [0, 1, 0, 1]

        arm = owner.parent
        if arm.isPlayingAction():
            frame = arm.getActionFrame()
        else:
            frame = 0

        arm.playAction('button-armatureAction', frame, 5)

        # Signal the squad if it's a person
        other = cont.sensors['Collision'].hitObject
        comp = other.get('_component', None)
        if comp is not None:
            set_id = group.get('id', None)
            if set_id is None:
                # No other buttons in the set
                return

            ai = bge.logic.game.ai.getAIController(comp)
            if ai is not None:
                owner['standing'] = ai
                squad = list(ai.squad)
                if not len(squad):
                    # No squad members
                    return

                # Find other buttons in the set
                buttons = []
                objects = bge.logic.getCurrentScene().objects
                for ob in objects:
                    if ob.name == 'button' and ob is not owner and ob.groupObject.get('id', None) == set_id:
                        # Check for standing in case the buttons are really close and the player is
                        # moving between them.
                        if not ob.groupObject.get('button', False) or ob.get('standing', None) is ai:
                            if ob.groupObject['button']:
                                # Force last button to de-press without waiting another frame
                                forget_button(ob)

                            buttons.append(ob)

                # Assign to squad members based on distance
                for b in buttons:
                    n = None
                    d = 0.0
                    for s in squad:
                        dist = b.getDistanceTo(s.component.owner)
                        if n is None or dist < d:
                            n = s
                            d = dist

                    if n is not None:
                        # Assign button to this AI
                        n.go_to_button(b)
                        squad.remove(n)

    else:
        forget_button(owner)


def forget_button(owner):
    group = owner.groupObject
    if not group['button']:
        return

    owner.groupObject['button'] = False
    owner.color = [1, 0, 0, 1]

    arm = owner.parent
    if arm.isPlayingAction():
        frame = arm.getActionFrame()
    else:
        frame = 5

    arm.playAction('button-armatureAction', frame, 0)

    ai = owner.get('standing', None)
    if ai is not None:
        owner['standing'] = None
        for s in ai.squad:
            s.forget_location()