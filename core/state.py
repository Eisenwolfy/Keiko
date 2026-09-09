from dataclasses import dataclass, field
from enum import Enum
from events import Modality, VoiceEventType, GestureEventType, TextEventType, Event
from typing import Any

class ProcessingStage(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"

@dataclass
class Trigger:
    modality: Modality
    type: VoiceEventType | GestureEventType | TextEventType
    keyword: str | None = None

    def comparison(self, ev: Event) ->bool:
        if (self.keyword is None or self.keyword == getattr(ev, "text", "")) and self.modality == ev.modality and self.type == ev.type:
            return True
        else:
            return False

@dataclass
class Session:
    name: str
    start_trigger: Trigger
    end_trigger: Trigger
    cache: dict[str, Any] = field(default_factory=dict)
    intermediate_trigger: Trigger | None = None

@dataclass
class State:
    processing_stage: ProcessingStage
    activation_modalities: set[Modality] = field(default_factory=set)
    active_session: Session | None = None