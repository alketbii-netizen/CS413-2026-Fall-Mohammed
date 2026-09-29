"""Shared, documented limits (kept in one place so Model, the constructor
reader, and the docs never disagree with each other)."""

# F3 / constructor_reader.MAX_SOURCE_BYTES: maximum accepted source size.
MAX_SOURCE_BYTES = 64 * 1024  # 64 KiB

# F10 / backend timeout bound: how long a single Interpret call may run
# before the request is treated as a backend failure and the model is
# freed up again, so a nonterminating program cannot leave the
# application permanently busy.
INTERPRET_TIMEOUT_SECONDS = 5.0
