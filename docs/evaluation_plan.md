# Evaluation Plan

## Evaluation Objectives

Establish a clear, incremental evaluation strategy for incident extraction outputs.

## Field-Level Evaluation

Evaluate each `IncidentRecord` field independently to identify strengths and weaknesses.

### Exact Match Fields

- `report_id`
- `operator`
- `train_id`
- `location`
- `component`

Exact match evaluation is appropriate when the expected value is a discrete identifier or a textual field with low acceptable variation.

### Normalized Match Fields

- `incident_datetime`
- `system`
- `severity`

For these fields, compare normalized values rather than raw text. Examples:
- datetimes normalized to ISO 8601
- system and severity mapped to the defined enums

### Classification Fields

- `system`
- `severity`

These fields represent categorical assignments and should be evaluated on accuracy and confusion patterns.

### Qualitative Review Fields

- `symptom`
- `service_impact`
- `source_text`
- `source_spans`

These fields benefit from human review for completeness, relevance, and fidelity to source meaning.

## Baseline-First Approach

Start with a simple baseline rather than an end-to-end deployed system.

- Define clear baseline fixtures and expected outputs for sample reports
- Validate schema consistency and field-level coverage
- Use the baseline to anchor future improvements and avoid premature optimization

## Future LLM Evaluation Approach

Plan future evaluation for natural-language methods while keeping the current scope documentation-focused.

- Measure LLM outputs against the same field-level schema
- Compare exact and normalized matches on standardized evaluation data
- Use human review on ambiguous or open-ended fields like `symptom` and `service_impact`
- Track changes in confidence calibration and error patterns over time