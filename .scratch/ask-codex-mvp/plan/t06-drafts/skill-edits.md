Ticket-06 SKILL.md edits (apply after the red runs):

1. Step 0 — the consultation-type table gains a row, and a rule above the table:

   **Follow-up first.** If the conversation already holds an earlier consultation's claims about the same question or Plan, and this consultation is about those claims — following up on claims you marked investigate, or re-checking the revised Plan they reviewed — the type is **follow-up**. Otherwise pick one of the four types below; a review-loop consultation with no earlier consultation on that Plan is a **second opinion**. A follow-up runs only when the user asks for it, or as a consented proactive consultation inside a fix or review loop (see Proactive consultations); otherwise you may mention in one line that a follow-up with Codex is possible, but never start one on your own.

   Table row:
   | **follow-up** | an earlier consultation's claims need verifying (marked investigate) or the Plan they reviewed was revised | carried claims | the carried claims in the fixed line form, plus the revised Plan when re-checking | secrets; claims you did not carry |

   Carried claims: for "follow up on what you marked investigate", every claim you marked investigate; for a re-check of a revised Plan, every claim of the earlier consultation on that Plan that was not rejected.

2. Proactive consultations — replace the review-loop bullet's first words:
   "**Review-loop consultations** are second opinions — or follow-ups when an earlier consultation in this conversation already reviewed that Plan (carry its claims): include the Plan …" (keep the fixed reshape sentence for second opinions).

3. Step 7 — framing list gains `prompts/framing/follow-up.md`; `{{context}}` for a follow-up: one line per carried claim in the fixed form
   `<id> [<your disposition>] <statement> — Claude: <reason>` (e.g. `C2 [investigate] renderProfile treats an empty object as 'user not found' — Claude: not yet confirmed that no other path renders it`), then the revised Plan text when re-checking. Never resume or fork a Codex session — a follow-up is a new run exactly like any other.

4. Step 10 — after "Unstructured reply", add **Follow-up reply**:
   Keep item 1. Then one line per carried claim, in this form, word for word:
   `<id> [<followup_status>] <statement> — Updated disposition: <adopt|reject|investigate> — <reason>`
   A carried claim missing from the reply, or with a `null` status, is shown as `<id> [no status returned]`.
   New claims with `followup_status` = `new-blocking` go under the heading `New blocking claim from Codex`, each with a disposition. A new claim that is not `new-blocking` is omitted — neither presented nor mentioned.

5. prompts/consultation.md rule 4: "… and `followup_status` = `null` unless the Consultation type section above tells you to report follow-up statuses."
6. New file prompts/framing/follow-up.md (see follow-up.md in this folder).
