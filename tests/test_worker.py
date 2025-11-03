from __future__ import annotations

import pytest

pytest.importorskip("redis")

from app.workers.audio import process_audio_metadata


def test_process_audio_metadata_returns_meta() -> None:
    result = process_audio_metadata("att-1", codec="opus", duration=1200, waveform=[0, 1, 2])
    assert result["attachment_id"] == "att-1"
    assert result["meta"]["codec"] == "opus"
