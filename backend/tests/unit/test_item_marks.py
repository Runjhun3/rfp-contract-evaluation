from app.ingest.item_marks import possible_item_marks


def test_parts_that_add_up_give_every_total_an_item_can_reach():
    # "Meeting criteria: 4 Marks; Prior experience with Government: 3 Marks" (RFP B.2)
    assert possible_item_marks([], ["4", "3"]) == ["3", "4", "7"]
    assert possible_item_marks([], ["6", "3"]) == ["3", "6", "9"]
    assert possible_item_marks([], ["2", "2", "1.5"]) == ["1.5", "2", "3.5", "4", "5.5"]


def test_slabs_are_kept_as_they_are_and_bad_or_zero_values_dropped():
    assert possible_item_marks(["5", "3", "4"], []) == ["3", "4", "5"]
    assert possible_item_marks(["3.0", "x", "0", ""], []) == ["3"]
    assert possible_item_marks([], []) == []
