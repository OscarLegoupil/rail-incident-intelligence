# Extraction Schema

This document describes the fields in the `IncidentRecord` schema and their intended meaning.

## Fields

### `report_id`
- Type: `string`
- Required: yes
- Meaning: unique identifier for the source incident report or record
- Example: `"INC-2026-0001"`
- Notes: should be stable across re-processing and cannot be empty

### `operator`
- Type: `string`
- Required: no
- Meaning: name or identifier of the operator responsible for the train or asset
- Example: `"North Rail"`
- Notes: may be omitted for generic or anonymized reports; do not infer proprietary names without a synthetic/public-style substitute

### `train_id`
- Type: `string`
- Required: no
- Meaning: trainset or vehicle identifier associated with the incident
- Example: `"T-452"`
- Notes: may be a unit number, roster code, or other vehicle label; inconsistent formatting is expected

### `incident_datetime`
- Type: `datetime`
- Required: no
- Meaning: the date and time when the incident occurred or was reported
- Example: `"2026-05-22T14:30:00Z"`
- Notes: use a parsable ISO 8601 representation; leave blank if source text does not provide a reliable timestamp

### `location`
- Type: `string`
- Required: no
- Meaning: physical location associated with the incident
- Example: `"Platform 3, Central Station"`
- Notes: may be a depot, station, route segment, or facility; ambiguous references should be captured verbatim when possible

### `system`
- Type: `IncidentSystem` enum
- Required: yes
- Meaning: the primary technical system involved in the incident
- Example: `"doors"`
- Notes: choose `unknown` when the system cannot be confidently determined; only the defined enum values are valid

### `component`
- Type: `string`
- Required: no
- Meaning: specific component or asset within the affected system
- Example: `"left sliding door mechanism"`
- Notes: may be highly variable and should reflect the source language when available

### `symptom`
- Type: `string`
- Required: yes
- Meaning: concise description of the observed failure, fault, or issue
- Example: `"door failed to close on departure"`
- Notes: this is the primary incident narrative and must not be empty

### `severity`
- Type: `IncidentSeverity` enum
- Required: yes
- Meaning: impact or seriousness of the incident
- Example: `"high"`
- Notes: use `unknown` when severity cannot be confidently assigned; a separate severity metric may be introduced later

### `service_impact`
- Type: `string`
- Required: no
- Meaning: description of the incident's operational impact
- Example: `"service delay of 10 minutes"`
- Notes: optional narrative field for consequences rather than root cause

### `confidence`
- Type: `float`
- Required: yes
- Meaning: numeric score representing extraction or classification confidence
- Example: `0.82`
- Notes: must be between 0.0 and 1.0; currently a placeholder for model or rule confidence

### `source_text`
- Type: `string`
- Required: no
- Meaning: original text from the source report used to derive the record
- Example: `"At 14:30 the left door failed to close on departure."`
- Notes: storing original text supports auditability and review

### `source_spans`
- Type: `list[SourceSpan]`
- Required: no
- Meaning: span-level provenance for extracted fields within the source text
- Example:
  - `field_name`: `"symptom"`
  - `text`: `"left door failed to close"`
  - `page`: `1`
  - `start_char`: `18`
  - `end_char`: `44`
- Notes: spans are optional and should only be included when source alignment is available

## SourceSpan Fields

### `field_name`
- Type: `string`
- Meaning: the target field associated with the text span
- Example: `"location"`

### `text`
- Type: `string`
- Meaning: the exact substring from the source document
- Example: `"Central Station"`

### `page`
- Type: `integer` or `null`
- Meaning: page number in the source document, when available
- Example: `1`

### `start_char` / `end_char`
- Type: `integer` or `null`
- Meaning: character offsets for the span in the original text
- Example: `start_char: 12`, `end_char: 27`
- Notes: both offsets must be non-negative and end must be greater than or equal to start when provided