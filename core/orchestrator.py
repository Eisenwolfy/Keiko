import asyncio
import logging
from state import Session, State, ProcessingStage
from events import Event

logger = logging.getLogger("orchestrator")


class Orchestrator:
    def __init__(self, sessions: dict[str, Session] | None = None):
        self.state = State(ProcessingStage.IDLE)
        self.sessions = sessions if sessions is not None else {}
        self._lock = asyncio.Lock()

    async def handle_event(self, event: Event) -> None:
        try:
            async with self._lock:
                await self._process(event)
        except Exception:
            logger.exception(f"Failed to process event {event.id}")

    async def _process(self, event: Event) -> None:
        active_session = self.state.active_session

        if active_session is not None:
            if active_session.end_trigger.comparison(event):
                logger.info(f"session done: {active_session.name} cache={active_session.cache}")
                self.state.active_session = None
            else:
                active_session.cache.setdefault(event.modality.value, []).append(event)
            return

        for session in self.sessions.values():
            if session.start_trigger.comparison(event):
                self.state.active_session = session
                return

        # TODO: LLM call — not ready yet
        await self._to_llm(event)

    async def _to_llm(self, event: Event) -> None:
        logger.info(f"to LLM: {event}")
