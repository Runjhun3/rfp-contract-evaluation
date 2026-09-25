from datetime import date
from decimal import Decimal

from app.evaluate.parse_amount import amount_matches, parse_amounts
from app.evaluate.parse_date import date_matches, parse_dates
from app.evaluate.quote_match import quote_score

TOL = Decimal("0.01")


def test_amount_formats():
    assert Decimal("90600000") in parse_amounts("INR 9.06 Crore")
    assert Decimal("90600000") in parse_amounts("Rs. 9,06,00,000/-")
    assert Decimal("90600000") in parse_amounts("₹ 906 lakh")
    assert Decimal("90600000") in parse_amounts("value 9.06 Cr (inclusive of GST)")


def test_amount_match_tolerance():
    assert amount_matches("90600000", "INR 9.06 Crore", TOL)[0]
    assert amount_matches("90623000", "INR 9.06 Crore", TOL)[0]
    assert not amount_matches("68000000", "INR 9.06 Crore", TOL)[0]


def test_dates_day_first():
    full, _ = parse_dates("completed on 03.04.2023")
    assert full == [date(2023, 4, 3)]
    full, _ = parse_dates("dated 31st March 2023")
    assert date(2023, 3, 31) in full
    full, _ = parse_dates('Work Order dated 18" June 2022 (% 6.00 Cr)')   # OCR noise
    assert date(2022, 6, 18) in full


def test_month_only_date():
    ok, shown = date_matches("2021-12-01", "Year in which Project took place | Dec 2021 — Jun 2022")
    assert ok and "month only" in shown
    assert date_matches("2022-06-30", "Dec 2021 — Jun 2022")[0]
    assert not date_matches("2023-06-30", "Dec 2021 — Jun 2022")[0]


def test_quote_exact_and_fuzzy():
    page = "Letter of Completion\nThe assignment was  successfully COMPLETED on 31.03.2023."
    assert quote_score("the assignment was successfully completed on 31.03.2023", page) == 100
    ocr = "The assignrnent was successfu1ly completed on 31.03.2023"
    assert quote_score(ocr, page) >= 90
    assert quote_score("contract value of Rs 5 crore", page) < 90
