# NSDF criteria block (example of evaluation_prompt.criteria_block)

Tender data, not a prompt file. In production this text lives in the DB and
is approved by a human. Source: RFP_Document_NSDF.pdf, Annexure III, pp. 34–35.

```text
CRITERION A.1  (max 16 marks, max 8 items)
RFP text: "Successfully carried out PMU assignments in Sports domain with minimum
duration of 01 year with Central/State govt. sports department."
Eligible only if ALL are true:
  - PMU assignment for a Central or State Government sports department
  - Completed
  - Duration >= 12 months
  - Awarded on or before {{bid_due_minus_12m}}
Marks: 2 per item.

CRITERION A.2  (max 10 marks, max 5 items)
RFP text: "Experience of executing sports consulting projects with project value of
Rs. 1 crore and above with central/state government sports departments/sports
promotion organizations."
Eligible only if ALL are true:
  - Sports consulting project for a central/state govt sports department or a
    sports promotion organisation
  - Completed
  - Value >= Rs 1,00,00,000
Marks by value:
  - > 1 Cr and <= 2 Cr : 1
  - > 2 Cr and <= 5 Cr : 1.5
  - > 5 Cr             : 2

CRITERION A.3  (max 10 marks, max 4 items)
RFP text: "Experience in executing consulting projects of value more than 5 Crs with
a Central/State Government Department each having minimum duration of one (1) year."
Eligible only if ALL are true:
  - Consulting project for a Central or State Government department (any sector)
  - Completed
  - Value > Rs 5,00,00,000
  - Duration >= 12 months
Marks: 2.5 per item.

CRITERION B.1  Project Manager, 1 CV  (max 8 marks)
  - Meeting criteria (4): MBA/PGDM (preferably Marketing or Sales) OR Master's in
    Economics / Sports Management / relevant field, AND >= 10 years in CSR /
    Fundraising / Project Management / Business Development / Strategic
    Partnerships / Growth / Marketing / Sales. Else 0.
  - Prior experience in sports sector and/or government and public sector (4). Else 0.

CRITERION B.2  Senior Consultant (Sports), 3 CVs  (max 21 marks, 7 per CV)
  - Meeting criteria (3 per CV): MBA/PGDM (preferably Marketing or Sales) OR
    Master's in Economics / Sports Management / BTech / relevant field, AND
    >= 7 years in the same fields as B.1. Else 0.
  - Prior experience in sports sector and/or government and public sector (4 per CV). Else 0.

CV RULE: more CVs than required for a position -> 0 marks for that position
(Annexure III, Note 3).
```
