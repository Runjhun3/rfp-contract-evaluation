"""Deleting a project or a firm, and when it is refused.

A project is only hidden (tender.deleted_at): its bids, runs, scores and committee
decisions stay on record. It cannot be deleted while a job for it is waiting or
running, because the worker would go on writing to it.

A firm is removed from the shared firm list only while no project holds its bid or
results. Rows of projects it was merely ticked in, with nothing uploaded, go with it.
"""
from app.db import q_bids, q_projects


def delete_project(cur, tender_id: str, user_id: str) -> str | None:
    """None when the project is deleted, else why it is not."""
    if q_projects.get_project(cur, tender_id) is None:
        return "Project not found"
    if q_projects.open_jobs(cur, tender_id):
        return "This project is being read or evaluated. Delete it once that has finished."
    q_projects.mark_deleted(cur, tender_id, user_id)
    return None


def delete_firm(cur, bidder_id: str) -> str | None:
    """None when the firm is deleted, else why it is not."""
    firm = q_bids.bidder(cur, bidder_id)
    if firm is None:
        return "Firm not found"
    if firm["bids"]:
        projects = "1 project" if firm["bids"] == 1 else f"{firm['bids']} projects"
        return (f"{firm['short_name']} has a bid or results in {projects}, so it stays on "
                "record. Untick it to leave it out of this project.")
    q_bids.delete_bidder(cur, bidder_id)
    return None
