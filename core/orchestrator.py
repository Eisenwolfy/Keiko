from state import Session, State, ProcessingStage
from events import Event


class Orchestrator:
    def __init__(self, sessions: dict[str, Session] | None = None):
        self.state = State(ProcessingStage.IDLE)
        self.sessions = sessions if sessions is not None else {}

    def handle_event(self, event: Event) -> None:
        active_session = self.state.active_session

        if active_session is not None:
            if active_session.end_trigger.comparison(event):
                print(f"[session done: {active_session.name}] cache={active_session.cache}")
                self.state.active_session = None
            else:
                active_session.cache[event.id] = event
            return

        for session in self.sessions.values():
            if session.start_trigger.comparison(event):
                self.state.active_session = session
                return

        # TODO: LLM call
        print(f"[to LLM] {event}")