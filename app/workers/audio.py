from __future__ import annotations

from dataclasses import dataclass

from redis import Redis
from rq import Queue

from app.core.config import settings


@dataclass
class AudioMeta:
    codec: str
    duration: int
    waveform: list[int]


def enqueue_audio_processing(attachment_id: str, *, codec: str, duration: int, waveform: list[int]) -> str:
    redis = Redis.from_url(settings.rq_redis_url)
    queue = Queue("audio", connection=redis)
    job = queue.enqueue(process_audio_metadata, attachment_id, codec=codec, duration=duration, waveform=waveform)
    return job.id


def process_audio_metadata(attachment_id: str, *, codec: str, duration: int, waveform: list[int]) -> dict[str, object]:
    return {
        "attachment_id": attachment_id,
        "meta": AudioMeta(codec=codec, duration=duration, waveform=waveform).__dict__,
    }
