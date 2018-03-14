from characters.character import Character


class BlueCrew(Character):
    config = Character.config.copy()
    config['parts'] = 'bluecrew-parts'
    config['icon'] = 'icon-bluecrew'

class OrangeCrew(Character):
    config = Character.config.copy()
    config['parts'] = 'orangecrew-parts'
    config['icon'] = 'icon-orangecrew'

class YellowCrew(Character):
    config = Character.config.copy()
    config['parts'] = 'yellowcrew-parts'
    config['icon'] = 'icon-yellowcrew'

class RedCrew(Character):
    config = Character.config.copy()
    config['parts'] = 'redcrew-parts'
    config['icon'] = 'icon-redcrew'

class GrayCrew(Character):
    config = Character.config.copy()
    config['parts'] = 'graycrew-parts'
    config['icon'] = 'icon-graycrew'

crewmen = {}
crewmen['blue'] = BlueCrew
crewmen['orange'] = OrangeCrew
crewmen['yellow'] = YellowCrew
crewmen['red'] = RedCrew
crewmen['gray'] = GrayCrew

def register(cont):
    owner = cont.owner.parent.parent
    if not 'component' in owner:
        owner['component'] = crewmen[cont.owner.name.split('crew-')[0]](owner)
