from nudging import session_state


def setup_function(_):
    session_state.reset()


def test_no_visits_means_zero_pressure():
    count, domain = session_state.get_distraction_pressure(now=1_000_000)
    assert count == 0
    assert domain is None


def test_visits_accumulate_within_window():
    session_state.record_distraction_visit("reddit.com", now=1000)
    session_state.record_distraction_visit("x.com", now=1010)
    count, domain = session_state.get_distraction_pressure(now=1020)
    assert count == 2
    assert domain == "x.com"


def test_visits_outside_window_are_pruned():
    session_state.record_distraction_visit("reddit.com", now=1000)
    later = 1000 + session_state.PRESSURE_WINDOW_SECONDS + 1
    count, domain = session_state.get_distraction_pressure(now=later)
    assert count == 0
    assert domain is None


def test_reset_clears_state():
    session_state.record_distraction_visit("reddit.com", now=1000)
    session_state.reset()
    count, _ = session_state.get_distraction_pressure(now=1000)
    assert count == 0
