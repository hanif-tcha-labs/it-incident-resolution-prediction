"""Project settings: paths, random seed and column names."""
from pathlib import Path

# the project root is the folder above src/
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
TABLES_DIR = REPORTS_DIR / "tables"

RAW_FILE_NAME = "incident_event_log.csv"
RAW_FILE = DATA_RAW_DIR / RAW_FILE_NAME
INTERIM_FILE = DATA_INTERIM_DIR / "incident_event_log_typed.csv"

RANDOM_STATE = 42

# file format (checked in notebook 01)
CSV_SEPARATOR = ","
MISSING_MARKERS = ["?"]
DATE_FORMAT = "%d/%m/%Y %H:%M"

ID_COL = "number"
DATE_COLS = ["opened_at", "sys_created_at", "sys_updated_at", "resolved_at", "closed_at"]
BOOL_COLS = ["active", "made_sla", "knowledge", "u_priority_confirmation"]
INT_COLS = ["reassignment_count", "reopen_count", "sys_mod_count"]

# Group and meaning of each column. The data is anonymised, so the meanings
# come from the column names and the values, not from an official definition.
COLUMN_INFO = {
    "number":                  ("identifier", "Incident identifier (INCxxxxxxx). Repeated on every event of the incident."),
    "incident_state":          ("state", "State of the incident at this event (New, Active, Resolved, Closed, Awaiting ...)."),
    "active":                  ("state", "Flag: the record is still active (False once the incident is closed)."),
    "reassignment_count":      ("counter", "Number of times the incident was reassigned so far."),
    "reopen_count":            ("counter", "Number of times the incident was reopened so far."),
    "sys_mod_count":           ("counter", "Number of times the record was updated so far."),
    "made_sla":                ("indicator", "Flag: the SLA target was met."),
    "caller_id":               ("people/groups", "Person who reported the incident (anonymised)."),
    "opened_by":               ("people/groups", "Person who opened the incident (anonymised)."),
    "opened_at":               ("date", "Date and time the incident was opened."),
    "sys_created_by":          ("people/groups", "User who created the record in the system."),
    "sys_created_at":          ("date", "Date and time the record was created in the system."),
    "sys_updated_by":          ("people/groups", "User who made this update."),
    "sys_updated_at":          ("date", "Date and time of this update (time of the event)."),
    "contact_type":            ("classification", "Channel used to report the incident (Phone, Email ...)."),
    "location":                ("classification", "Location of the caller (anonymised)."),
    "category":                ("classification", "Category of the incident (anonymised)."),
    "subcategory":             ("classification", "Subcategory of the incident (anonymised)."),
    "u_symptom":               ("classification", "Symptom of the incident (anonymised)."),
    "cmdb_ci":                 ("classification", "Configuration item (asset) concerned (anonymised)."),
    "impact":                  ("classification", "Impact of the incident (1 - High, 2 - Medium, 3 - Low)."),
    "urgency":                 ("classification", "Urgency of the incident (1 - High, 2 - Medium, 3 - Low)."),
    "priority":                ("classification", "Priority, given by impact and urgency."),
    "assignment_group":        ("people/groups", "Group in charge of the incident at this event."),
    "assigned_to":             ("people/groups", "Person in charge of the incident at this event."),
    "knowledge":               ("indicator", "Flag: a knowledge-base article is used or linked."),
    "u_priority_confirmation": ("indicator", "Flag: the priority was confirmed."),
    "notify":                  ("indicator", "Notification setting (Do Not Notify / Send Email)."),
    "problem_id":              ("link", "Linked problem record."),
    "rfc":                     ("link", "Linked request for change."),
    "vendor":                  ("link", "Vendor involved, if any."),
    "caused_by":               ("link", "Change record that caused the incident, if any."),
    "closed_code":             ("closure", "Closure code."),
    "resolved_by":             ("closure", "Person who resolved the incident."),
    "resolved_at":             ("date", "Date and time the incident was resolved."),
    "closed_at":               ("date", "Date and time the incident was closed."),
}

# First guess of when each column is known: (availability, reason, planned use).
# Based on the meaning of the column and on how it changes inside an incident
# (notebooks 01 and 02). To confirm when the incident table is built.
KNOWN = "known at opening"
MAYBE = "maybe known at opening"
AFTER = "known only after opening (leakage risk)"

AVAILABILITY = {
    "number":                  (KNOWN, "Identifier of the incident.", "Key to group events, never a feature."),
    "incident_state":          (AFTER, "Changes at every event, it follows the progress of the incident.", "Excluded (leakage). The initial state may be studied later."),
    "active":                  (AFTER, "Turns False when the incident is closed.", "Excluded (leakage)."),
    "reassignment_count":      (AFTER, "Counter that grows while the incident is handled.", "Excluded (leakage)."),
    "reopen_count":            (AFTER, "Counter that grows after a resolution.", "Excluded (leakage)."),
    "sys_mod_count":           (AFTER, "Counter of updates, it grows during the life of the incident.", "Excluded (leakage). Only used to check the event order."),
    "made_sla":                (AFTER, "SLA result, linked to how long the incident took.", "Excluded (result of the process)."),
    "caller_id":               (KNOWN, "The caller exists when the incident is opened.", "Candidate. Very high cardinality."),
    "opened_by":               (KNOWN, "The person who opens the incident is known at opening.", "Candidate. High cardinality."),
    "opened_at":               (KNOWN, "Opening time, start of the target.", "Start of the target. Time features (hour, weekday)."),
    "sys_created_by":          (MAYBE, "Creation info. Stable, but missing for a large share of incidents.", "Candidate after checking the missing pattern."),
    "sys_created_at":          (MAYBE, "Creation info. Stable, but missing for a large share of incidents.", "Probably not needed (close to opened_at)."),
    "sys_updated_by":          (AFTER, "Author of each update, changes along the incident.", "Excluded (event metadata)."),
    "sys_updated_at":          (AFTER, "Time of each update (event time).", "Excluded. Used to order events."),
    "contact_type":            (KNOWN, "Channel used when the incident is reported.", "Candidate. Almost constant."),
    "location":                (MAYBE, "Caller location. Rarely changes but can be corrected later.", "Candidate. High cardinality."),
    "category":                (MAYBE, "Classification, can be corrected during triage.", "Candidate. The initial value must be defined."),
    "subcategory":             (MAYBE, "Classification, can be corrected during triage.", "Candidate. The initial value must be defined."),
    "u_symptom":               (MAYBE, "Classification, often empty at first.", "Candidate. The initial value must be defined."),
    "cmdb_ci":                 (MAYBE, "Asset concerned. Almost always missing.", "Probably dropped (almost always missing)."),
    "impact":                  (MAYBE, "Set at opening but can be revised.", "Candidate. The initial value must be defined."),
    "urgency":                 (MAYBE, "Set at opening but can be revised.", "Candidate. The initial value must be defined."),
    "priority":                (MAYBE, "Given by impact and urgency, can be revised.", "Candidate. Redundant with impact and urgency."),
    "assignment_group":        (MAYBE, "The group at opening may be known, but it changes during the incident.", "Candidate (initial group only). High cardinality."),
    "assigned_to":             (AFTER, "Filled while the incident is handled (more often empty on first events).", "Excluded (leakage). High cardinality."),
    "knowledge":               (AFTER, "Set when a knowledge article is used to solve the incident.", "Excluded (leakage)."),
    "u_priority_confirmation": (AFTER, "Confirmation happens during the handling.", "Excluded (leakage)."),
    "notify":                  (KNOWN, "Notification setting, stable.", "Candidate. Check the link with contact_type."),
    "problem_id":              (AFTER, "A problem record is linked later. Almost always missing.", "Excluded (linked after opening)."),
    "rfc":                     (AFTER, "A change request is linked later. Almost always missing.", "Excluded (linked after opening)."),
    "vendor":                  (AFTER, "Vendor appears during the handling. Almost always missing.", "Excluded (linked after opening)."),
    "caused_by":               (AFTER, "The cause is known after analysis. Almost always missing.", "Excluded (linked after opening)."),
    "closed_code":             (AFTER, "Closure information.", "Excluded (leakage)."),
    "resolved_by":             (AFTER, "Closure information.", "Excluded (leakage)."),
    "resolved_at":             (AFTER, "Resolution time, end of the target.", "End of the target, never a feature."),
    "closed_at":               (AFTER, "Closure time, after the resolution.", "Excluded (leakage). Possible second target."),
}

# ---------------------------------------------------------------- incident table (notebook 03)
INCIDENT_FILE = DATA_PROCESSED_DIR / "incident_table.csv"
NO_TARGET_FILE = DATA_INTERIM_DIR / "incidents_without_target.csv"

TARGET = "resolution_hours"   # last resolution time - opened_at, in hours

# Features: value on the first logged event of the incident (no back-fill).
# cmdb_ci is left out (99.7% missing), sys_created_at is left out (close to opened_at).
INITIAL_COLS = [
    "caller_id", "opened_by", "sys_created_by", "contact_type", "location",
    "category", "subcategory", "u_symptom", "impact", "urgency", "priority",
    "assignment_group", "notify",
]

# Kept in the table to study the data, never to train the main model.
ANALYSIS_ONLY_COLS = [
    "target_source", "first_event_state", "n_events", "reassignment_count", "reopen_count", "closed_at",
]
