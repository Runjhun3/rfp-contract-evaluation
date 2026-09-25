You label pages of a bid submitted against a government RFP.
For each page below, choose exactly one page_type:

- CLAIM_SUMMARY: a table listing projects/CVs the bidder claims for a
  criterion (often titled "Response to Evaluation Criteria" or "Annexure VII")
- PROJECT_HEADER: the first page of one project's section (project name,
  client, "Evaluation Criteria A1/A2/A3", "Credential-N", "Project - N")
- WORK_ORDER: work order, letter of award, contract, agreement
- COMPLETION_CERT: completion / performance certificate from the client
- CA_CERT: chartered accountant certificate of value or payment
- CV: curriculum vitae page
- DECLARATION: forms, undertakings, power of attorney, EMD, empanelment
- MARKETING: firm profile, brochure, presentation slides
- BLANK: blank or divider page
- OTHER: none of the above

Also return criterion_hint if the page names a criterion code (A.1, A2, B.1 ...),
normalised to "A.1" form, else null.
If a page shows a GeM bid number, return it in gem_bid_no, else null.

Return exactly this JSON:
{"pages": [{"pdf_page_no": 1, "page_type": "...", "criterion_hint": null, "gem_bid_no": null}]}

PAGES
{{pages}}
