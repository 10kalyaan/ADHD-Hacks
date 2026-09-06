"""
Session-only "distraction pressure" signal.

Not the personalization/learning loop the plan explicitly puts out of scope
(hackathon-master-plan.md, section 3) — there's no profile, no persistence,
nothing written to VectorAI DB, and it resets to zero every time the Flask
process restarts. It's just an in-memory counter of how many times someone
has bounced onto a distraction domain recently, used to decide how sharp the
nudge should be and how many cards to show.

Why this exists: task-initiation research on ADHD attention says choice
overload makes activation *harder*, not easier — so the more someone is
already bouncing between distraction tabs, the fewer options a nudge should
show them (see ranking.py). One tab, one clear next step beats a list.
"""

import time
from collections import deque

# Only visits inside this window count toward "pressure" — a bounce from an
# hour ago shouldn't still be escalating the tone of the next nudge.
PRESSURE_WINDOW_SECONDS = 15 * 60

_distraction_visits = deque()


def record_distraction_visit(domain, now=None):
    now = now if now is not None else time.time()
    _distraction_visits.append((now, domain))
    _prune(now)


def get_distraction_pressure(now=None):
    """Returns (count_in_window, most_recent_domain_or_None)."""
    now = now if now is not None else time.time()
    _prune(now)
    if not _distraction_visits:
        return 0, None
    return len(_distraction_visits), _distraction_visits[-1][1]


def reset():
    _distraction_visits.clear()


def _prune(now):
    cutoff = now - PRESSURE_WINDOW_SECONDS
    while _distraction_visits and _distraction_visits[0][0] < cutoff:
        _distraction_visits.popleft()
