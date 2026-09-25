You label pages of a bid submitted against a government RFP.

CRITERIA OF THIS TENDER (code — meaning)
{{criteria_list}}

For each page below:
1. Choose exactly one page_type:
   - CLAIM_SUMMARY: a table listing projects/CVs the bidder claims for a criterion
   - PROJECT_HEADER: the first page of one project's section (name, client, often a
     credential/project number)
   - WORK_ORDER: work order, letter of award, contract, agreement
   - COMPLETION_CERT: completion / performance certificate from the client
   - CA_CERT: chartered accountant certificate of value or payment
   - CV: curriculum vitae page
   - DECLARATION: forms, undertakings, power of attorney, EMD, empanelment
   - MARKETING: firm profile, brochure, presentation slides
   - BLANK: blank or divider page
   - OTHER: none of the above
2. For CLAIM_SUMMARY, PROJECT_HEADER and CV pages, set criterion_code to the
   criterion above whose MEANING the page responds to. Bidders often use
   different words or numbering than the RFP (e.g. "Sports consulting
   assignments above INR 1 crore" responds to the criterion about sports
   consulting projects of value 1 crore and above). The bidder's own label is
   only a hint. If nothing fits, null. Give map_confidence 0.0-1.0.
3. If a page shows a GeM bid number, return it in gem_bid_no, else null.

Return exactly this JSON:
{"pages": [{"pdf_page_no": 1, "page_type": "...", "criterion_code": null,
            "map_confidence": null, "gem_bid_no": null}]}

PAGES
{{pages}}
