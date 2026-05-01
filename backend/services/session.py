"""Session storage — in-memory session state for active pipelines."""

# In-memory session store: session_id -> {status, state, progress, error}
sessions: dict = {}
