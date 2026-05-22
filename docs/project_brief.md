# Project Brief

## Problem Statement

Rail operator maintenance reports are often written in free text and vary by format, making it difficult to extract structured incident data consistently. This project aims to define the initial extraction schema and supporting documentation for a system that converts heterogeneous maintenance narratives into a normalized incident record format.

## Target Users

- Data engineers and analytics teams working on rail incident monitoring
- Maintenance planners needing structured incident summaries
- Reporting engineers validating downstream data ingestion
- Portfolio reviewers evaluating DS/ML engineering project structure

## Expected Inputs

- Primary input: `txt` incident report files
- Future input targets: `pdf`, `docx`
- Inputs are expected to contain one or more narrative incident descriptions with identifiers, timing, and failure details

## Expected Outputs

- A normalized incident record per report, represented as structured JSON or Pydantic-compatible data
- Fields include report identifier, incident time, operator, system and component information, symptom description, severity, and optional metadata such as confidence and source spans

## Constraints

- Current implementation is documentation-first; no extraction engine is included yet
- The initial schema is limited to the fields defined by `IncidentRecord`
- Inputs are assumed to be clean enough to map to structured fields, but may be partially incomplete
- Ad hoc operator-specific terminology is not yet standardized

## Assumptions

- Reports are processed one incident record at a time
- Symptom text is mandatory, because it is the primary incident description
- Severity and system may be unknown when not clearly stated
- Confidence values are used as a normalization placeholder for future extraction output

## Out-of-Scope Items

- No extraction or parser implementation is being added at this stage
- No model training, LLM integration, Streamlit UI, or deployment work
- No proprietary client or vendor-specific content
- No production-quality data pipeline or live ingestion system

## Confidentiality Note

This project uses synthetic or public-style data only. Do not include proprietary operator names, confidential maintenance records, or client-specific information.