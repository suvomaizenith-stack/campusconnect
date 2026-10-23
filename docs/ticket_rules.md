# Ticket rules

- Statuses: `waiting` (no online staff) -> `assigned` -> `in_progress` -> `resolved`. `self_resolved` is a student flag; the ticket is kept.
- Assignment: online staff in the category's department with the fewest open tickets; if none, status `waiting`. When staff go online, waiting tickets are assigned (priority first, then oldest).
- Ticket code: `CC-` plus the id padded to 4 digits.
- Every status, assignment or detail change writes a `status_history` row.
- Duplicates: auto-linked to an existing group with `dup_review='pending'`. Staff Confirm (stay linked) or Separate (unlink and recount). Every student keeps their own ticket.
- Priority score = category base + severity*10 + report_count*5. Tier: critical (>=100), high (>=75), normal (>=55), later (below).
- Thresholds live in `config.py`: hotspot at 3 reports, critical at 5, window 24 h.
- Severity 3 always creates a ticket and an alert.
