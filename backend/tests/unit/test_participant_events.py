import pytest

from app import criteria_edits, participants


@pytest.fixture
def firms(monkeypatch):
    """A fake firm list and project; returns the events recorded."""
    state = {"list": {"Firm A Pvt Ltd": {"bidder_id": "a", "short_name": "Firm A"}},
             "ticked": {"a": True, "b": False}, "events": []}
    names = {"a": "Firm A", "b": "Firm B"}
    q_bids = participants.q_bids
    monkeypatch.setattr(q_bids, "participants", lambda cur, t: [
        {"bidder_id": b, "short_name": names[b], "included": on}
        for b, on in state["ticked"].items()])

    def tick(cur, t, ids):
        state["ticked"] = {b: b in ids for b in {*state["ticked"], *ids}}
    monkeypatch.setattr(q_bids, "set_participants", tick)
    monkeypatch.setattr(q_bids, "add_participant",
                        lambda cur, t, b: state["ticked"].update({b: True}))
    monkeypatch.setattr(q_bids, "bidder_by_legal_name", lambda cur, legal: state["list"].get(legal))

    def add(cur, legal, short):
        names["c" if legal not in state["list"] else state["list"][legal]["bidder_id"]] = short
        return state["list"].get(legal, {"bidder_id": "c"})["bidder_id"]
    monkeypatch.setattr(q_bids, "add_bidder", add)
    monkeypatch.setattr(participants.q_events, "add", lambda cur, t, u, action, target, d:
                        state["events"].append((t, action, target, d.get("note"))))
    return state["events"]


def test_ticking_and_unticking_record_only_real_changes(firms):
    participants.save(None, "t", ["a", "b"], "u")
    participants.save(None, "t", ["a", "b"], "u")               # nothing changed
    participants.save(None, "t", ["b"], "u")
    assert firms == [("t", "Participant added", "Firm B", None),
                     ("t", "Participant removed", "Firm A", None)]


def test_a_new_firm_is_added_and_a_known_one_renamed_only_when_its_name_changes(firms):
    participants.add_firm(None, "t", "Firm C LLP", "Firm C", "u")
    participants.add_firm(None, "t", "Firm A Pvt Ltd", "Firm A", "u")  # same name, ticked
    participants.add_firm(None, "t", "Firm A Pvt Ltd", "A & Co", "u")
    assert firms == [(None, "Firm added", "Firm C", "Firm C LLP"),
                     ("t", "Participant added", "Firm C", None),
                     (None, "Firm renamed", "A & Co", "Firm A")]


def test_the_approved_criteria_are_kept_as_the_trail_shows_them():
    row = {"code": "A.1", "title": "Projects", "stage": "TECHNICAL", "max_marks": 12,
           "considered": False, "kind": None}
    kept = criteria_edits.snapshot([row])[0]
    assert kept["code"] == "A.1" and kept["max_marks"] == "12"
    assert kept["considered"] == "left out" and kept["kind"] is None
