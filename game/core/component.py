import bge


class Component:
    def __init__(self, owner):
        self.owner = owner
        self._subscribed_events = []

        if callable(getattr(self, 'update', None)):
            bge.logic.core.register(self)

    def subscribe_to_event(self, subject):
        assert(subject not in self._subscribed_events)

        observers = bge.logic.core.observers
        if not subject in observers.keys():
            observers[subject] = []

        observers[subject].append(self)
        self._subscribed_events.append(subject)

    def send_event(self, subject, data):
        observers = bge.logic.core.observers.get(subject, None)
        if observers is not None:
            for observer in observers:
                if not observer.owner.invalid:
                    eval("observer.handle_event_{}(data)".format(subject))

    def unsubscribe_from_events(self):
        observers = bge.logic.core.observers
        for subject in self.subscribed_events:
            observers[subject].remove(self)

        self._subscribed_events = []
