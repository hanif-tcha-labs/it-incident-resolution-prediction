# Data dictionary

| Column | Type | Group | Meaning | Example value | Availability at opening |
|---|---|---|---|---|---|
| number | object | identifier | Incident identifier (INCxxxxxxx). Repeated on every event of the incident. | INC0019396, INC0044260, INC0005927 | Known at opening |
| incident_state | object | state | State of the incident at this event (New, Active, Resolved, Closed, Awaiting ...). | Active, New, Resolved | Known only after opening (leakage risk) |
| active | bool | state | Flag indicating whether the record is still active (False once the incident is closed). | True, False | Known only after opening (leakage risk) |
| reassignment_count | int64 | counter | Number of times the incident has been reassigned to another group or person so far. | 0 to 27 | Known only after opening (leakage risk) |
| reopen_count | int64 | counter | Number of times the incident has been reopened so far. | 0 to 8 | Known only after opening (leakage risk) |
| sys_mod_count | int64 | counter | Number of times the record has been updated so far (event counter). | 0 to 129 | Known only after opening (leakage risk) |
| made_sla | bool | indicator | Flag indicating whether the SLA target was met. | True, False | Known only after opening (leakage risk) |
| caller_id | object | people/groups | Identifier of the person who reported the incident (anonymised). | Caller 1904, Caller 290, Caller 4514 | Known at opening |
| opened_by | object | people/groups | Person who opened the incident (anonymised). | Opened by 17, Opened by 24, Opened by 131 | Known at opening |
| opened_at | datetime64[ns] | date | Date and time the incident was opened. | 2016-02-29 to 2017-02-16 | Known at opening |
| sys_created_by | object | people/groups | User who created the record in the system. | Created by 10, Created by 13, Created by 62 | Maybe known at opening |
| sys_created_at | datetime64[ns] | date | Date and time the record was created in the system. | 2016-02-29 to 2017-01-27 | Maybe known at opening |
| sys_updated_by | object | people/groups | User who made this update. | Updated by 908, Updated by 44, Updated by 60 | Known only after opening (leakage risk) |
| sys_updated_at | datetime64[ns] | date | Date and time of this update (timestamp of the event). | 2016-02-29 to 2017-02-18 | Known only after opening (leakage risk) |
| contact_type | object | classification | Channel used to report the incident (Phone, Email, etc.). | Phone, Self service, Email | Known at opening |
| location | object | classification | Location of the caller (anonymised). | Location 204, Location 161, Location 143 | Maybe known at opening |
| category | object | classification | Category of the incident (anonymised). | Category 26, Category 42, Category 53 | Maybe known at opening |
| subcategory | object | classification | Subcategory of the incident (anonymised). | Subcategory 174, Subcategory 223, Subcategory 175 | Maybe known at opening |
| u_symptom | object | classification | Symptom of the incident (anonymised). | Symptom 491, Symptom 534, Symptom 387 | Maybe known at opening |
| cmdb_ci | object | classification | Configuration item (asset) concerned (anonymised). | cmdb_ci 31, cmdb_ci 49, cmdb_ci 7 | Maybe known at opening |
| impact | object | classification | Impact of the incident (1 - High, 2 - Medium, 3 - Low). | 2 - Medium, 3 - Low, 1 - High | Maybe known at opening |
| urgency | object | classification | Urgency of the incident (1 - High, 2 - Medium, 3 - Low). | 2 - Medium, 1 - High, 3 - Low | Maybe known at opening |
| priority | object | classification | Priority, derived from impact and urgency. | 3 - Moderate, 4 - Low, 2 - High | Maybe known at opening |
| assignment_group | object | people/groups | Group in charge of the incident at this event. | Group 70, Group 25, Group 24 | Maybe known at opening |
| assigned_to | object | people/groups | Person in charge of the incident at this event. | Resolver 17, Resolver 13, Resolver 194 | Known only after opening (leakage risk) |
| knowledge | bool | indicator | Flag indicating whether a knowledge-base article is used or linked. | False, True | Known only after opening (leakage risk) |
| u_priority_confirmation | bool | indicator | Flag indicating whether the priority has been confirmed. | False, True | Known only after opening (leakage risk) |
| notify | object | indicator | Notification setting (Do Not Notify / Send Email). | Do Not Notify, Send Email | Known at opening |
| problem_id | object | link | Identifier of a linked problem record. | Problem ID 14, Problem ID 2, Problem ID 52 | Known only after opening (leakage risk) |
| rfc | object | link | Identifier of a linked request for change. | CHG0000132, CHG0001230, CHG0000047 | Known only after opening (leakage risk) |
| vendor | object | link | Vendor involved, if any. | code 8s, Vendor 1, Vendor 3 | Known only after opening (leakage risk) |
| caused_by | object | link | Change record that caused the incident, if any. | CHG0000097, CHG0000132, CHG0001327 | Known only after opening (leakage risk) |
| closed_code | object | closure | Closure or resolution code. | code 6, code 7, code 9 | Known only after opening (leakage risk) |
| resolved_by | object | closure | Person who resolved the incident. | Resolved by 15, Resolved by 11, Resolved by 103 | Known only after opening (leakage risk) |
| resolved_at | datetime64[ns] | date | Date and time the incident was resolved. | 2016-02-29 to 2017-02-17 | Known only after opening (leakage risk) |
| closed_at | datetime64[ns] | date | Date and time the incident was closed. | 2016-02-29 to 2017-02-18 | Known only after opening (leakage risk) |