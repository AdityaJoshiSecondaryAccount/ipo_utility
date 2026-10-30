"""
Hand-off between the pages of the pipeline.

All pages run in ONE `manage.py test` process on ONE database (see run_tests.py), so data created by an
earlier page is still there for a later one. What a later page cannot know from the database alone is
WHICH rows an earlier page created on purpose. A page that creates pipeline data records it here, and the
page that checks it asserts against exactly that record instead of against global row counts:

    from test_cases import pipeline_state
    pipeline_state.record("groupwise", "add_payment", {"entries": [...]})      # producer
    pipeline_state.get("groupwise", "add_payment")                             # consumer (None if it never ran)

Rules for pipeline data: a page that records it never edits or deletes it afterwards, and every page that
reads it must be able to say what to do when it is missing (seed a minimum itself, or skip with a reason).
`dump()` writes the record to $PW_STATE_FILE (if set) so a failed run can be inspected.
"""
import json
import os
import uuid

# One id per run: a remark marker that tells this run's rows from anything else in the database.
RUN_ID = uuid.uuid4().hex[:8]

_state = {}


def marker(page):
    """Unique remark text for rows a page creates, e.g. 'PW-groupwise-1a2b3c4d'."""
    return f"PW-{page}-{RUN_ID}"


def record(page, key, data):
    _state.setdefault(page, {})[key] = data
    dump()


def get(page, key, default=None):
    return _state.get(page, {}).get(key, default)


def pages():
    return {page: sorted(keys) for page, keys in _state.items()}


def dump():
    path = os.environ.get("PW_STATE_FILE")
    if path:
        with open(path, "w") as handle:
            json.dump({"run_id": RUN_ID, "state": _state}, handle, indent=2, default=str)
