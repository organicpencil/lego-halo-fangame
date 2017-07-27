def pull(cont):
    if not cont.sensors[0].positive:
        return

    owner = cont.owner

    # Update instance property if applicable
    group = owner.groupObject
    if group is not None:
        group['pulled'] = True
        # TODO - network update

    # Animations
    owner.playAction('lever-pull', 0, 32)
    for c in list(owner.children[0].children):
        c.endObject()

    status = owner.parent
    status.playAction('lever-status', 0, 32)
    for c in status.children:
        if c.name.split('_')[0] == 'glow':
            c.playAction('lever-statusglow', 0, 32)