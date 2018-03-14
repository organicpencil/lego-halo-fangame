from characters.character import Character


class Marine(Character):
    config = Character.config.copy()
    config['hp'] = 4
    config['parts'] = 'marine-parts'
    config['icon'] = 'icon-marine'

def register(cont):
    owner = cont.owner.parent.parent
    if not 'component' in owner:
        owner['component'] = Marine(owner)
