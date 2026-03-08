## ADDED Requirements

### Requirement: Mandatory critique after every screenshot
The system prompt SHALL instruct the LLM to run a quality checklist after every screenshot, before responding to the user.

#### Scenario: Screenshot taken
- **WHEN** the LLM takes a screenshot of its work
- **THEN** it MUST evaluate the image against the checklist (proportions, alignment, materials, silhouette, floating parts, scale) before any response

### Requirement: Auto-fix loop
The system prompt SHALL instruct the LLM to automatically fix issues found during critique and re-screenshot.

#### Scenario: Issues found
- **WHEN** the critique checklist identifies problems (e.g., gaps between parts, missing materials)
- **THEN** the LLM fixes the issues in the script, re-executes, and takes a new screenshot without involving the user

#### Scenario: Max iterations
- **WHEN** the LLM has performed 3 fix-and-check iterations and issues remain
- **THEN** it shows the current result to the user with an honest assessment and asks for guidance

### Requirement: No false positives
The system prompt SHALL instruct the LLM to never claim the result "looks good" without having run the checklist.

#### Scenario: LLM responds about quality
- **WHEN** the LLM makes any quality assessment of its output
- **THEN** it MUST have run the critique checklist first and reference specific checks that passed
