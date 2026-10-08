You label pages of a bid submitted against a government RFP.

CRITERIA OF THIS TENDER (code — meaning)
{{criteria_list}}

ELIGIBILITY REQUIREMENTS OF THIS TENDER (code — meaning — proof the RFP asks for)
{{eligibility_list}}

For each page under PAGES:
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
   - BLANK: blank page, divider page, or a page that only carries a section or
     annexure title (no project or person details). Never PROJECT_HEADER.
   - OTHER: none of the above
2. For CLAIM_SUMMARY pages, set criterion_code to the ONE criterion above whose
   MEANING the listed items are claimed for. Bidders often use different words
   or numbering than the RFP (e.g. "Sports consulting assignments above INR 1
   crore" responds to the criterion about sports consulting projects of value
   1 crore and above). If the summary lists items for more than one criterion
   (e.g. one table for all proposed team members), set criterion_code to null.
3. For PROJECT_HEADER and CV pages, set criterion_code to the criterion the page
   responds to by meaning (for a CV: the position proposed). The bidder's own
   label is only a hint. If nothing fits, null. Give map_confidence 0.0-1.0.
   Criteria marked [whole bid] are scored once on the bidder as a whole (e.g.
   turnover, net worth, a certification). For ANY other page that is evidence
   for such a criterion (a certificate, financial statement, declaration or
   summary that states it), set criterion_code to that criterion, whatever its
   page_type, with map_confidence.
4. Set item_start = true only on the FIRST page of one project's section or of
   one CV (the page that names the project/person). Continuation pages of the
   same project or CV are false. On an item_start page set title to the
   project name, or to "person name, position proposed" for a CV, copied from
   the page. Otherwise title is null.
5. If a page shows a GeM bid number, return it in gem_bid_no, else null.
6. In eligibility, list the code of EVERY eligibility requirement above that the
   page is evidence for, by meaning: the document the RFP asks for as proof, or
   any page that states the fact the requirement is about (e.g. a certificate of
   incorporation, an auditor's turnover certificate, a signed declaration, an
   empanelment letter). A page can prove several requirements, and a page that
   belongs to a project or CV above can still prove one. A page that only
   mentions a requirement without proving it (e.g. an index or a blank format)
   proves none. Otherwise [].
7. PAGES BEFORE are the pages just before the first page under PAGES, already
   labelled (their labels are shown). Use them only to tell whether the first
   pages under PAGES continue a document or a project or CV section that began
   there, or start a new one. Do not label them again.

Return exactly this JSON, with one entry for each page under PAGES and none for
the PAGES BEFORE:
{"pages": [{"pdf_page_no": 1, "page_type": "...", "criterion_code": null,
            "map_confidence": null, "item_start": false, "title": null,
            "gem_bid_no": null, "eligibility": []}]}

PAGES BEFORE (context only)
{{pages_before}}

PAGES
{{pages}}
