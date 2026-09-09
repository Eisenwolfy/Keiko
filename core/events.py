from dataclasses import dataclass, field
import time
import uuid
from enum import Enum

class Modality(Enum):
    TEXT = "text"
    VOICE = "voice"
    GESTURE = "gesture"

class VoiceEventType(Enum):
    WAKE = "wake word"
    SPEECH = "request words"
    BYE = "bye word"

class GestureEventType(Enum):
    BASE = "base gesture"
    CONTINUOUS = "continuous gesture"
    CUSTOM = "user's gesture"

class TextEventType(Enum):
    TEXT = "text"

@dataclass
class Event:
    type: VoiceEventType | GestureEventType | TextEventType
    modality: Modality
    timestamp: float = field(default_factory = time.perf_counter)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass(kw_only=True)
class VoiceEvent(Event):
    type: VoiceEventType
    text: str
    confidence: float
    modality: Modality = Modality.VOICE

@dataclass(kw_only=True)
class GestureEvent(Event):
    type: GestureEventType
    coordinates: tuple[float, float]
    confidence: float
    modality: Modality = Modality.GESTURE

@dataclass(kw_only=True)
class TextEvent(Event):
    type: TextEventType
    text: str
    modality: Modality = Modality.TEXT
  
