"""In-memory Redis-Streams double (Sahil · Week 2 dev/test backend).

Implements the subset of the redis-py Streams API that ``TelemetryPipeline``
relies on — ``xadd`` / ``xlen`` / ``xrange`` / ``xgroup_create`` /
``xreadgroup`` / ``xack`` — with real **consumer-group + pending-entry**
semantics so at-least-once delivery can be tested without a live Redis.

IDs are a monotonic ``"<n>-0"`` counter (deterministic, unlike wall-clock ms),
which keeps ordering comparisons and tests reproducible.
"""

from __future__ import annotations

from typing import Any


def _id_tuple(entry_id: str) -> tuple[int, int]:
    ms, _, seq = entry_id.partition("-")
    return int(ms), int(seq or 0)


def _id_gt(a: str, b: str) -> bool:
    return _id_tuple(a) > _id_tuple(b)


def _id_ge(a: str, b: str) -> bool:
    return _id_tuple(a) >= _id_tuple(b)


class _Group:
    __slots__ = ("last_delivered", "pending")

    def __init__(self, last_delivered: str) -> None:
        self.last_delivered = last_delivered
        self.pending: dict[str, str] = {}  # entry_id -> consumer


class MemoryStreams:
    """Minimal, dependency-free stand-in for a redis-py Streams client."""

    def __init__(self) -> None:
        self._streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._groups: dict[tuple[str, str], _Group] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"{self._counter}-0"

    def xadd(
        self,
        name: str,
        fields: dict[str, Any],
        maxlen: int | None = None,
        approximate: bool = True,
    ) -> str:
        entry_id = self._next_id()
        self._streams.setdefault(name, []).append(
            (entry_id, {k: str(v) for k, v in fields.items()})
        )
        if maxlen is not None and len(self._streams[name]) > maxlen:
            self._streams[name] = self._streams[name][-maxlen:]
        return entry_id

    def xlen(self, name: str) -> int:
        return len(self._streams.get(name, []))

    def xrange(self, name: str, min: str = "-", max: str = "+") -> list[tuple[str, dict[str, str]]]:
        return list(self._streams.get(name, []))

    def xtrim(self, name: str, maxlen: int, approximate: bool = True) -> int:
        entries = self._streams.get(name, [])
        excess = max(0, len(entries) - maxlen)
        if excess:
            self._streams[name] = entries[excess:]
        return excess

    def xgroup_create(
        self, name: str, groupname: str, id: str = "$", mkstream: bool = False
    ) -> bool:
        if name not in self._streams:
            if not mkstream:
                raise KeyError(f"stream {name!r} does not exist")
            self._streams[name] = []
        if (name, groupname) in self._groups:
            raise ValueError("BUSYGROUP Consumer Group name already exists")
        if id in ("$",):
            last = self._streams[name][-1][0] if self._streams[name] else "0-0"
        elif id in ("0", "0-0"):
            last = "0-0"
        else:
            last = id
        self._groups[(name, groupname)] = _Group(last)
        return True

    def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int | None = None,
    ) -> list[tuple[str, list[tuple[str, dict[str, str]]]]]:
        result: list[tuple[str, list[tuple[str, dict[str, str]]]]] = []
        for name, cursor in streams.items():
            group = self._groups[(name, groupname)]
            entries = self._streams.get(name, [])
            if cursor == ">":
                fresh = [(eid, f) for eid, f in entries if _id_gt(eid, group.last_delivered)]
                if count is not None:
                    fresh = fresh[:count]
                for eid, _ in fresh:
                    group.pending[eid] = consumername
                    group.last_delivered = eid
                result.append((name, fresh))
            else:
                pend = [
                    (eid, f) for eid, f in entries if eid in group.pending and _id_ge(eid, cursor)
                ]
                if count is not None:
                    pend = pend[:count]
                result.append((name, pend))
        return result

    def xack(self, name: str, groupname: str, *ids: str) -> int:
        group = self._groups[(name, groupname)]
        acked = 0
        for entry_id in ids:
            if group.pending.pop(entry_id, None) is not None:
                acked += 1
        return acked

    def xpending_count(self, name: str, groupname: str) -> int:
        """Number of delivered-but-unacked entries (test/introspection helper)."""
        return len(self._groups[(name, groupname)].pending)
