# Synthetic Dataset Conventions

## Overview

This document defines the conventions and principles governing the synthetic dataset for rail incident intelligence extraction. The dataset is designed to provide high-quality, manually labeled training data for developing and evaluating incident extraction models.

---

## Naming Conventions

### Report Files

- **Format**: `SRXXX.txt`
- **Prefix**: `SR` (Synthetic Report)
- **Numbering**: Zero-padded 3-digit sequential ID (001-999)
- **Example**: `SR001.txt`, `SR042.txt`
- **Location**: `data/synthetic/reports/`

### Label Files

- **Format**: `SRXXX.json`
- **Naming**: Matches corresponding report ID
- **Content**: JSON structure following `IncidentRecord` schema
- **Location**: `data/synthetic/labels/`
- **Requirement**: One label file per report, created together

### Field Naming

- **report_id**: Must match the SR identifier exactly (e.g., "SR001")
- **component**: Use snake_case with descriptive qualifiers
  - Example: `pneumatic_actuator_car3_door_b`, `temperature_control_valve`, `abs_sensor`
  - Format: `system_part_location_qualifier`

---

## Synthetic Data Principles

### Authenticity

- Reports reflect realistic maintenance operations and rail industry language
- Terminology aligned with standard rail maintenance documentation practices
- Time formats and identifiers follow operational conventions

### Representativeness

- **System Coverage**: All primary rail subsystems represented
  - Doors, Brakes, Propulsion, Signalling, HVAC, Passenger Information, Other
- **Severity Distribution**: Range from low to critical
- **Completeness**: Mix of complete and partial reports (some fields intentionally omitted)

### Quality Standards

- **No Confidentiality**: No real operational data, no actual train numbers from real service
- **No LLM Artifacts**: No synthetic metadata, no auto-generated comments or explanations within report text
- **High Manual Confidence**: All labels created with confidence = 1.0, ensuring ground truth quality
- **Traceability**: Every label linked to source text with character offsets

### Variability

The dataset intentionally includes variation across multiple dimensions:

1. **Report Structure**
   - Formal technical reports with structured sections
   - Brief field notes with minimal detail
   - Narrative descriptions with conversational tone
   - Standardized forms and log entries

2. **Writing Style**
   - Technical/formal (technical jargon, passive voice)
   - Casual/colloquial (conversational, abbreviated)
   - Mixed styles reflecting different reporter experience levels

3. **Field Completeness**
   - Some reports include all optional fields (operator, train_id, incident_datetime, location)
   - Others intentionally omit optional fields to represent incomplete information
   - Reports vary in specificity of component and location details

4. **Terminology**
   - Multiple synonyms for same concepts (e.g., "door actuator" vs "pneumatic cylinder")
   - Abbreviations and full terms mixed throughout dataset
   - Regional and colloquial terminology alongside formal terms

---

## Labeling Assumptions

### Confidence Level

- **All Labels**: confidence = 1.0
- **Justification**: Labels are manually curated for ground truth, not automatic extraction
- **Interpretation**: Represents high-quality human judgment, not model certainty

### Optional Fields

- **Fields set to null**: Indicate that information was not present or inferable from source
- **Operator**: Omitted when not mentioned or only given as initials in informal context
- **train_id**: Omitted when report doesn't identify the train
- **incident_datetime**: Omitted or estimated conservatively when not explicit
- **location**: Omitted when not specified

### Datetime Handling

- **Explicit times**: Converted to ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
- **Date only**: Set to typical business hours (08:00 or 14:00) when time not specified
- **Missing dates**: Left as null, not inferred from context
- **Example**: Report stating "24 March 2024" → "2024-03-24T09:00:00"

### System Classification

- **Single System**: Each report mapped to one primary system
- **Component Specificity**: Component field identifies the specific part when determinable
- **Hierarchy**: System chosen at subsystem level (e.g., "brakes" not "vehicle", "hvac" not "mechanical")

---

## Mapping Conventions

### IncidentSystem Enumeration

Map reports to the following system categories:

| System | Scope | Examples |
|--------|-------|----------|
| `doors` | Door mechanisms and actuators | Door seals, pneumatic cylinders, door motors |
| `brakes` | Brake systems and components | Brake pressure, ABS sensors, brake cylinders |
| `propulsion` | Traction motors and drive systems | Motor vibration, yaw dampers, bearings |
| `signalling` | Signal detection and processing | Signal gaps, timing issues |
| `hvac` | Heating, ventilation, air conditioning | Fans, compressors, thermostats, seals |
| `passenger_information` | Passenger-facing systems | Announcements, displays, intercoms |
| `other` | Systems not in primary categories | Structural, mechanical support |
| `unknown` | Insufficient information to classify | Only used when system truly cannot be determined |

### Severity Classification

| Severity | Criteria | Examples |
|----------|----------|----------|
| `critical` | Immediate safety risk; vehicle out of service | Stuck doors preventing boarding, complete brake failure, severe suspension damage |
| `high` | Significant degradation; likely service removal | Door actuator leaks, motor vibration exceeding spec, ABS dropout during braking |
| `medium` | Operational degradation; affects service quality | HVAC malfunction, pressure variations, minor sensor issues |
| `low` | Minor issue; passenger comfort or non-essential function | Speaker failure, display dim, cosmetic seal damage |
| `unknown` | Information insufficient to assess severity | Reserved for truly ambiguous cases |

### Component Naming

- **Format**: `system_part_location_qualifier`
- **Specificity**: Include sufficient detail to identify the part uniquely
- **Examples**:
  - `pneumatic_actuator_car3_door_b` (specific location and door)
  - `fan_motor_relay` (component and related part)
  - `abs_sensor` (specific subsystem sensor)
  - `temperature_control_valve` (functional description)
  - `primary_yaw_damper_truck_assembly` (assembly location)

### Source Spans

**Purpose**: Link extracted labels back to source text for validation and training transparency

**Fields**:
- `field_name`: Which label field this text supports (e.g., "symptom", "component")
- `text`: Exact substring from source document
- `start_char`: Character offset of text start (0-indexed)
- `end_char`: Character offset of text end (exclusive)
- `page`: Page number (null for single-page reports)

**Guidelines**:
- Capture minimal sufficient text
- Prioritize direct quotes over paraphrasing
- Include context when ambiguity exists
- Multiple spans allowed per field when text is distributed

---

## Ambiguity Handling

### Partially Specified Components

**Situation**: Component is mentioned but location or exact part is ambiguous

**Resolution**: 
- Include available specificity in component name
- Use source_spans to reference the exact text
- Set component to null only if no part information available

**Example**: "Door won't open" → component: "door_platform_side_car_2" (inferred from context)

### Missing Temporal Information

**Situation**: Report lacks specific date or time

**Resolution**:
- Leave incident_datetime as null if date cannot be reasonably inferred
- Do not fabricate dates
- If date mentioned but no time, use representative business hours

**Example**: Report dated "12 May 2024" with no time → "2024-05-12T08:00:00"

### Optional Field Omission

**Situation**: Field legitimately not inferable from source

**Resolution**:
- Set to null (do not leave blank strings)
- Example: operator not mentioned → "operator": null

### Multiple Potential Systems

**Situation**: Issue could relate to multiple systems (e.g., brake delay could be signalling or brake)

**Resolution**:
- Choose primary system causing the symptom
- Prioritize most direct cause: brake system if brake-related components implicated
- Document in source_spans if ambiguous

### Inconsistency Between Text and Inference

**Situation**: Report text contradicts reasonable mechanical inference

**Resolution**:
- Prioritize explicit statement from report
- Do not override with assumed mechanical knowledge
- Let model learn from labeled data as-is

---

## Dataset Statistics

### Coverage by System

- **Doors**: 3 reports (SR001, SR005, SR009)
- **Brakes**: 2 reports (SR002, SR008)
- **HVAC**: 2 reports (SR003, SR006)
- **Propulsion**: 2 reports (SR004, SR010)
- **Passenger Information**: 1 report (SR007)

### Coverage by Severity

- **Critical**: 2 reports (SR005, SR010)
- **High**: 4 reports (SR001, SR002, SR004, SR008)
- **Medium**: 3 reports (SR003, SR006, SR009)
- **Low**: 1 report (SR007)

### Optional Field Completion

- **Full reports** (all optional fields): SR001, SR004, SR008
- **Partial reports** (some nulls): SR002, SR003, SR005, SR006, SR007, SR009, SR010

---

## Usage Notes

### For Training

- Use as-is for supervised learning of incident extraction
- High confidence labels suitable for ground truth
- Variety in structure and completeness helps model robustness

### For Evaluation

- Reports represent realistic incident documentation diversity
- Performance across different report styles indicates generalization capability
- Missing fields test model behavior on incomplete information

### For Expansion

- Follow naming and labeling conventions for consistency
- Maintain 10:1 ratio of reports to labels
- Continue varying report style and information completeness
- Use this document as reference for new label creation
