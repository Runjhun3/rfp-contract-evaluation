"""Who takes part in a project, and the shared firm list, with each change recorded as
an audit event (docs/decisions.md D-054): a participant added or removed, a firm added,
renamed or deleted. Saving with nothing changed records nothing. No reason is asked:
the event says who and when."""
from app.db import q_bids, q_events


def save(cur, tender_id: str, bidder_ids: list[str], user_id: str) -> None:
    """Exactly the ticked firms take part (q_bids.set_participants)."""
    before = {p["bidder_id"]: p["included"] for p in q_bids.participants(cur, tender_id)}
    q_bids.set_participants(cur, tender_id, bidder_ids)
    for p in q_bids.participants(cur, tender_id):
        if p["included"] != before.get(p["bidder_id"], False):
            _participant_event(cur, tender_id, p, user_id)


def add_firm(cur, tender_id: str, legal_name: str, short_name: str, user_id: str) -> str:
    """Add a firm to the list (or rename the one with this legal name) and tick it."""
    known = q_bids.bidder_by_legal_name(cur, legal_name)
    bidder_id = q_bids.add_bidder(cur, legal_name, short_name)
    name = short_name or legal_name
    if known is None:
        q_events.add(cur, None, user_id, "Firm added", name,
                     {"bidder_id": bidder_id, "note": legal_name})
    elif known["short_name"] != name:
        q_events.add(cur, None, user_id, "Firm renamed", name,
                     {"bidder_id": bidder_id, "note": known["short_name"], "new": name})
    was = {p["bidder_id"]: p["included"] for p in q_bids.participants(cur, tender_id)}
    q_bids.add_participant(cur, tender_id, bidder_id)
    if not was.get(bidder_id):
        _participant_event(cur, tender_id, {"bidder_id": bidder_id, "short_name": name,
                                            "included": True}, user_id)
    return bidder_id


def firm_deleted(cur, firm: dict, user_id: str) -> None:
    """Before an unused firm is deleted: the event, and in each project it was ticked in,
    its removal (the project's own trail would otherwise lose it)."""
    for tender_id in q_bids.firm_projects(cur, firm["bidder_id"]):
        q_events.add(cur, tender_id, user_id, "Participant removed", firm["short_name"],
                     {"bidder_id": firm["bidder_id"], "note": "firm deleted"})
    q_events.add(cur, None, user_id, "Firm deleted", firm["short_name"],
                 {"bidder_id": firm["bidder_id"], "note": firm.get("legal_name")})


def _participant_event(cur, tender_id: str, p: dict, user_id: str) -> None:
    action = "Participant added" if p["included"] else "Participant removed"
    q_events.add(cur, tender_id, user_id, action, p["short_name"], {"bidder_id": p["bidder_id"]})
