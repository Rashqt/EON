"""
Event log: a chronological record of things that actually happened in the
simulation. Every entry here is appended at the moment the underlying
condition was detected by the engine -- nothing is written in advance or
inferred after the fact.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LogEvent:
    tick: int
    category: str  # "environment" | "species" | "population" | "extinction"
    text: str


class EventLog:
    def __init__(self, max_entries: int = 5000) -> None:
        self.entries: list[LogEvent] = []
        self.max_entries = max_entries

    def add(self, tick: int, category: str, text: str) -> None:
        self.entries.append(LogEvent(tick=tick, category=category, text=text))
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def recent(self, n: int = 20) -> list[LogEvent]:
        return self.entries[-n:]
