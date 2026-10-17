# Target definition

**Prediction moment:** When the incident is opened (`opened_at`).

**Target:** `resolution_hours` = time between `opened_at` and the last resolution, in hours.

**Resolution time:**
1. Use `resolved_at` when available.
2. Otherwise, use the time of the last event with state `Resolved`.
3. If the incident never reaches `Resolved`, it has no target.

Notebook 02 confirms that both methods give exactly the same result for the 23,362 incidents where both values are available.

**Why not `closed_at`?**

`closed_at` is usually much later than the actual resolution (median delay of about 120 hours). It mainly reflects the closing delay, not the resolution time.

**Incidents to consider:**

| Group | Number | Treatment |
|---|---:|---|
| Never resolved | 13 | Excluded and saved separately |
| Created already `Resolved` | 1,819 | Kept and flagged with `first_event_state` |
| Reopened incidents | 275 | Kept and flagged with `reopen_count > 0` |
| Resolved in under 1 hour | 7,503 | Kept |

The incidents created already `Resolved` will be tested with and without in notebooks 05 and 06. For reopened incidents, the target uses the last resolution.

**Unit:** Hours. The target is highly skewed (median: 22.1 h, 90th percentile: 381.5 h, maximum: 8,070 h). A log transformation will be tested later, with results converted back to hours for evaluation.