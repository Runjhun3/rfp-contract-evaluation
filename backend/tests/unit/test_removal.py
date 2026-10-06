import pytest

from app import removal

PROJECT = {"tender_id": "t", "name": "Hypothetical tender"}


@pytest.fixture
def deleted(monkeypatch):
    done = []
    monkeypatch.setattr(removal.q_projects, "mark_deleted", lambda cur, t, u: done.append(t))
    monkeypatch.setattr(removal.q_bids, "delete_bidder", lambda cur, b: done.append(b))
    return done


def test_a_project_is_hidden_unless_it_is_being_read_or_evaluated(monkeypatch, deleted):
    monkeypatch.setattr(removal.q_projects, "get_project", lambda cur, t: PROJECT)
    monkeypatch.setattr(removal.q_projects, "open_jobs", lambda cur, t: 1)
    assert "being read or evaluated" in removal.delete_project(None, "t", "u")
    monkeypatch.setattr(removal.q_projects, "open_jobs", lambda cur, t: 0)
    assert removal.delete_project(None, "t", "u") is None
    assert deleted == ["t"]


def test_a_missing_or_already_deleted_project_is_not_found(monkeypatch, deleted):
    monkeypatch.setattr(removal.q_projects, "get_project", lambda cur, t: None)
    assert removal.delete_project(None, "t", "u") == "Project not found"
    assert deleted == []


def test_a_firm_is_deleted_only_when_no_project_holds_its_bid_or_results(monkeypatch,
                                                                           deleted):
    firm = {"bidder_id": "b", "short_name": "Firm A", "legal_name": "Firm A Pvt Ltd", "bids": 2}
    events = []
    monkeypatch.setattr(removal.q_bids, "bidder", lambda cur, b: firm)
    monkeypatch.setattr(removal.participants.q_bids, "firm_projects", lambda cur, b: ["t1"])
    monkeypatch.setattr(removal.participants.q_events, "add",
                        lambda cur, t, u, action, target, details: events.append((t, action)))
    assert "bid or results in 2 projects" in removal.delete_firm(None, "b", "u")
    firm["bids"] = 0                                      # only ticked, nothing uploaded
    assert removal.delete_firm(None, "b", "u") is None
    assert deleted == ["b"]
    # Recorded first: its removal from the project it was ticked in, then the deletion.
    assert events == [("t1", "Participant removed"), (None, "Firm deleted")]
    monkeypatch.setattr(removal.q_bids, "bidder", lambda cur, b: None)
    assert removal.delete_firm(None, "b", "u") == "Firm not found"
