"""Required test 6: stream table lifecycle with an injected clock."""
import unittest

from server import streams


class FakeClock:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t


class TestStreamTable(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.t = streams.StreamTable(clock=self.clock, ttl=100, max_open=3)

    def test_exhaustion_and_repeat_next(self):
        sid = self.t.open(4)
        events, done = [], False
        while not done:
            batch, done = self.t.next(sid, 32)
            self.assertLessEqual(len(batch), 32)
            events += batch
        self.assertEqual(events[-1], {"event": "done"})
        self.assertEqual(self.t.next(sid, 5), ([], True))
        self.assertEqual(self.t.live_count(), 0)       # LAMBDA3 state released

    def test_close_then_unknown(self):
        sid = self.t.open(4)
        self.t.close(sid)
        with self.assertRaises(streams.UnknownStream):
            self.t.next(sid, 1)
        with self.assertRaises(streams.UnknownStream):
            self.t.close(sid)

    def test_unknown_id(self):
        with self.assertRaises(streams.UnknownStream):
            self.t.next("00000000-0000-0000-0000-000000000000", 1)

    def test_expiration_after_inactivity(self):
        sid = self.t.open(5)
        self.clock.t = 90
        self.t.next(sid, 1)                  # activity refreshes the lifetime
        self.clock.t = 180
        self.assertEqual(len(self.t.next(sid, 1)[0]), 1)
        self.clock.t = 281
        with self.assertRaises(streams.UnknownStream):
            self.t.next(sid, 1)
        self.assertEqual(len(self.t), 0)

    def test_exhausted_tombstone_expires(self):
        sid = self.t.open(4)
        while not self.t.next(sid, 32)[1]:
            pass
        self.clock.t = 101
        self.assertEqual(self.t.sweep(), 1)

    def test_open_limit(self):
        for _ in range(3):
            self.t.open(4)
        with self.assertRaises(streams.TooManyStreams):
            self.t.open(4)

    def test_ids_are_unique_uuids(self):
        import uuid
        ids = {self.t.open(4) for _ in range(3)}
        self.assertEqual(len(ids), 3)
        for i in ids:
            self.assertEqual(str(uuid.UUID(i)), i)


if __name__ == "__main__":
    unittest.main()
