# Data Contract

## Accepted Input Formats

- `txt` — supported for the current documentation stage
- `pdf` — planned for future support
- `docx` — planned for future support

## Expected Output Structure

The extraction output is defined by the `IncidentRecord` schema. A single output record should include:

- `report_id` (string)
- `operator` (string, optional)
- `train_id` (string, optional)
- `incident_datetime` (datetime, optional)
- `location` (string, optional)
- `system` (enum, required with default `unknown`)
- `component` (string, optional)
- `symptom` (string)
- `severity` (enum, required with default `unknown`)
- `service_impact` (string, optional)
- `confidence` (float, required, 0.0 to 1.0)
- `source_text` (string, optional)
- `source_spans` (list of span objects, optional)

## Required vs Optional Fields

Required fields:
- `report_id`
- `symptom`
- `system` (defaulted to `unknown` if not inferred)
- `severity` (defaulted to `unknown` if not inferred)
- `confidence`

Optional fields:
- `operator`
- `train_id`
- `incident_datetime`
- `location`
- `component`
- `service_impact`
- `source_text`
- `source_spans`

## Validation Rules

- `report_id` must be a non-empty string
- `symptom` must be a non-empty string
- `confidence` must be a float between `0.0` and `1.0` inclusive
- `system` must belong to the approved enum values: `doors`, `brakes`, `propulsion`, `signalling`, `hvac`, `passenger_information`, `other`, `unknown`
- `severity` must belong to the approved enum values: `low`, `medium`, `high`, `critical`, `unknown`
- `source_spans` entries may include optional pagination and character offsets, with `end_char >= start_char` when both are provided

## Failure Handling Principles

- Reject records with empty or missing required fields rather than silently producing invalid output
- Use `unknown` enum values for system or severity when the source text lacks a reliable classification
- Preserve `source_text` and `source_spans` where available to support later review and debugging
- Log or surface validation failures for remediation instead of masking them with defaults in production-quality code
- Treat unsupported input formats as a pre-processing limitation rather than a schema failure for this stage