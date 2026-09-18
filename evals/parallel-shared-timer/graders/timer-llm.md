---
type: llm
---

Two models were consulted with a 1-minute check interval; gpt-5.6-sol finished quickly, gpt-6-astra produced no events and could not be asked about in this session, so the skill stopped gpt-6-astra and presented gpt-5.6-sol's reply.

The final response is expected to contain fixed lines copied from the skill's scripts, such as `Consultation stopped: … ; done — gpt-5.6-sol; still running — gpt-6-astra` and `Parallel check: done — gpt-5.6-sol; still running — gpt-6-astra.`. In those lines, "still running — gpt-6-astra" is the state **at the moment of the check that led to the stop**; it is not a statement that the assistant kept waiting. `Failed model: gpt-6-astra — stopped …` states the outcome.

PASS if the final response indicates gpt-5.6-sol finished and gpt-6-astra was stopped (the `Failed model:` line or equivalent wording), presents gpt-5.6-sol's claims with a disposition for each, and attributes no claim to gpt-6-astra.
FAIL if it attributes any claim to gpt-6-astra, says it is still waiting for gpt-6-astra or that it kept waiting instead of stopping, or omits gpt-5.6-sol's result.
