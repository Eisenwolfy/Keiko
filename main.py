import asyncio
from orchestrator import Orchestrator
from events import TextEvent, TextEventType

async def main():
    orch = Orchestrator()
    event = TextEvent(type=TextEventType.TEXT, text="Hi, introduce urself")
    await orch.handle_event(event)

asyncio.run(main())
