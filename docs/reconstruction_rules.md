# Reconstruction rules: from the event log to one row per incident

**Code:** `src/reconstruction.py` (`build_incident_table`)  
**Notebook:** `03_target_and_incident_reconstruction.ipynb`

1. **Unit:** One row per `number` (incident). All incidents are included before removing those without a target.

2. **Event order:** Events are sorted by `sys_updated_at`. Original file order is kept when timestamps are equal. `sys_mod_count` is not used because it is unreliable for some incidents (notebook 02).

3. **Target:** Defined in `target_definition.md`.

4. **Features at opening:** The first event provides the values for `caller_id`, `opened_by`, `sys_created_by`, `contact_type`, `location`, `category`, `subcategory`, `u_symptom`, `impact`, `urgency`, `priority`, `assignment_group`, `notify` and `opened_at`.
   - The first event occurs a median of 0.02 hours after opening (99% within 0.82 hours).
   - Missing values are not filled using later events.
   - The last event is not used because some values change during incident handling.

5. **Excluded columns:**
   - Columns only available after opening: `state`, counters, SLA, `assigned_to`, `knowledge`, `u_priority_confirmation`, `sys_updated_*`, links (`problem_id`, `rfc`, `vendor`, `caused_by`) and closure fields.
   - `cmdb_ci`: empty in 99.7% of events.
   - `sys_created_at`: almost identical to `opened_at`.

6. **Analysis only:** `target_source`, `first_event_state`, `n_events`, `reassignment_count`, `reopen_count` and `closed_at` are not used in the main model.

7. **Exclusion:** Only incidents without a resolution time are removed. No outliers, missing values or duplicates are removed (notebook 02).

8. **Checks:** The notebook verifies one row per incident, non-negative targets, correct target calculations, column assignments, 200 randomly checked incidents and the saved output file.