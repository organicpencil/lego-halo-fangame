from characters.character import Character


class Johnson(Character):
    config = Character.config.copy()
    config['hp'] = 4
    config['parts'] = 'johnson-parts'
    config['icon'] = 'icon-johnson'

def register(cont):
    owner = cont.owner.parent.parent
    if not 'component' in owner:
        owner['component'] = Johnson(owner)
