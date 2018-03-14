from characters.character import Character


class Keyes(Character):
    config = Character.config.copy()
    config['hp'] = 4
    config['parts'] = 'keyes-parts'
    config['icon'] = 'icon-keyes'

def register(cont):
    owner = cont.owner.parent.parent
    if not 'component' in owner:
        owner['component'] = Keyes(owner)
