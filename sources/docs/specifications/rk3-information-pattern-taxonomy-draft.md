# RK3 Information Pattern Taxonomy and LLM Recognition Prompts

Draft version: 0.1  
Purpose: define layered information patterns that RK3 can recognize in source documents, extract into structured IR, and map to web-native publishing components.

This is not a visual design system. It sits before the design system:

```text
source content
→ information patterns
→ structured content objects
→ component recommendations
→ client design system styles the result
```

## Core idea

A long-form report is not just paragraphs. It contains recurring information structures:

- facts
- claims
- quotes
- examples
- questions
- recommendations
- comparisons
- data tables
- case studies
- policy arguments

RK3 should recognize those structures, extract their parts, and recommend treatments that help readers understand, compare, trust, or act.

## Suggested layer model

```text
Layer 0: Atomic evidence and inline signals
Layer 1: Content units
Layer 2: Compound structures
Layer 3: Page/section modules
Layer 4: Publication sections
Layer 5: Whole-publication archetypes
```

Each layer can contain objects from lower layers. For example, a case study may contain statistics, quotes, places, dates, organizations, and recommendations.

---

# Layer 0: Atomic evidence and inline signals

These are the smallest extractable signals. They may appear inside paragraphs, captions, tables, callouts, or footnotes.

## 0.1 Statistic

### Definition

A numeric fact presented as evidence, context, trend, scale, or outcome.

### Common indicators

- Numerals, percentages, currency, counts, rates, ratios, years
- Phrases like "increased by," "decreased by," "more than," "fewer than," "approximately," "nearly"
- Units: people, dollars, acres, tons, jobs, households, students, counties, percent, percentage points
- Comparators: "compared with," "from X to Y," "between 2020 and 2025"

### Extract fields

```json
{
  "pattern": "statistic",
  "value": "737,000",
  "unit": "people",
  "label": "FIM-eligible population",
  "qualifier": null,
  "time_period": "2026",
  "geography": "Oklahoma",
  "source_note_ref": "1",
  "surrounding_claim": "FIM-eligible population in Oklahoma is 737,000.",
  "confidence": 0.0
}
```

### Component opportunities

- Stat card
- Metric row
- Comparison card
- Data point in chart
- Pull quote/stat callout
- Interactive selector if repeated by geography/entity/time

---

## 0.2 Quotation

### Definition

Verbatim or near-verbatim words attributed to a person, group, document, or source.

### Common indicators

- Quotation marks
- Blockquote styling
- Em dash attribution
- Following line with name/title/organization
- Phrases like "said," "noted," "explained," "according to"
- Italicized or indented paragraph near an attribution

### Extract fields

```json
{
  "pattern": "quotation",
  "quote_text": "The partnership helped us align our work around shared outcomes.",
  "speaker_name": "Jane Smith",
  "speaker_title": "Program Director",
  "speaker_affiliation": "Example Community Coalition",
  "source_context": "case study",
  "topic": "cross-sector partnership",
  "is_pull_quote_candidate": true,
  "confidence": 0.0
}
```

### Component opportunities

- Pull quote
- Testimonial card
- Evidence sidebar
- Case study quote
- Hero quote
- Quote carousel, if multiple quotes share a theme

---

## 0.3 Claim

### Definition

A substantive assertion the report wants readers to believe.

### Common indicators

- Declarative statements
- Topic sentences
- Phrases like "this shows," "this demonstrates," "the evidence suggests," "we find that"
- Often followed by statistics, examples, quotes, citations, or recommendations

### Extract fields

```json
{
  "pattern": "claim",
  "claim_text": "Local food procurement can create stable demand for small and mid-sized family farms.",
  "claim_type": "causal",
  "supporting_evidence_refs": ["stat_12", "quote_4", "case_2"],
  "strength": "moderate",
  "scope": "statewide",
  "confidence": 0.0
}
```

### Component opportunities

- Key finding
- Summary card
- Evidence stack
- Claim/evidence/recommendation module

---

## 0.4 Recommendation / Action

### Definition

A proposed action, usually directed at a stakeholder.

### Common indicators

- Imperatives: "Increase," "Fund," "Create," "Adopt," "Require"
- Modal verbs: "should," "must," "can," "need to"
- Policy verbs: "expand," "establish," "invest," "coordinate," "evaluate"
- Often appears in "Recommendations," "Next Steps," "Actions," or "Policy Implications"

### Extract fields

```json
{
  "pattern": "recommendation",
  "action": "Establish a statewide FIM implementation timeline.",
  "actor": "state agency",
  "target": "FIM implementation",
  "rationale": "to reflect ongoing community engagement",
  "timeframe": "near term",
  "related_evidence_refs": ["claim_7", "stat_3"],
  "confidence": 0.0
}
```

### Component opportunities

- Recommendation card
- Action agenda
- Roadmap item
- Checklist
- Actor-by-action matrix

---

## 0.5 Entity

### Definition

A named person, organization, place, program, law, funder, agency, or initiative.

### Common indicators

- Proper nouns
- Abbreviations and defined acronyms
- "known as," "hereafter," parentheticals after full names
- Tables with organization/program names

### Extract fields

```json
{
  "pattern": "entity",
  "entity_text": "Food is Medicine",
  "entity_type": "program_or_field",
  "acronym": "FIM",
  "definition": "programs that connect food and health interventions",
  "first_seen_section": "Executive Summary",
  "aliases": ["FIM programs"],
  "confidence": 0.0
}
```

### Component opportunities

- Glossary
- Acronym helper
- Entity profile card
- Network/relationship diagram

---

## 0.6 Source note / citation

### Definition

A footnote, endnote, citation marker, or source reference supporting nearby content.

### Common indicators

- Superscript numbers
- Bracketed references
- Footnote/endnote sections
- "Source:" lines below charts/tables
- Citation-like parentheticals

### Extract fields

```json
{
  "pattern": "source_note",
  "marker": "1",
  "note_text": "Estimate based on 2026 population analysis.",
  "applies_to_refs": ["stat_2"],
  "source_type": "methodology_note",
  "url": null,
  "confidence": 0.0
}
```

### Component opportunities

- Accessible footnotes
- Expandable source note
- Data source panel
- Methodology appendix

---

## 0.7 Definition

### Definition

A sentence or block that explains what a term means.

### Common indicators

- "X is..."
- "X refers to..."
- "For purposes of this report..."
- Bolded term followed by explanatory text
- Glossary/list format

### Extract fields

```json
{
  "pattern": "definition",
  "term": "Food is Medicine",
  "definition_text": "A range of programs that use food-based interventions to improve health outcomes.",
  "scope_note": "as used in this report",
  "confidence": 0.0
}
```

### Component opportunities

- Definition callout
- Glossary item
- Tooltip
- Introductory explainer box

---

## 0.8 Date / timeline marker

### Definition

A date, period, milestone, deadline, or sequence marker.

### Common indicators

- Years, months, quarters
- "Phase 1," "Stage 4," "by 2030," "over five years"
- "Before," "after," "during," "following"

### Extract fields

```json
{
  "pattern": "timeline_marker",
  "label": "Stage 4",
  "date_or_period": null,
  "sequence_number": 4,
  "event_or_phase": "Implement Cross-Sector Solutions",
  "confidence": 0.0
}
```

### Component opportunities

- Timeline
- Process step
- Milestone card
- Roadmap

---

# Layer 1: Content units

These are paragraph-level or block-level structures.

## 1.1 Key finding

### Definition

A concise conclusion supported by evidence.

### Common indicators

- Appears in executive summary or findings section
- Headings like "Key Findings," "What We Found," "Findings"
- Often starts with a bold lead phrase followed by explanation
- Usually supported by statistics, examples, or citations

### Extract fields

```json
{
  "pattern": "key_finding",
  "title": "Local procurement can support farm income.",
  "summary": "Statewide FIM procurement could generate stable revenue for small and mid-sized farmers.",
  "supporting_evidence_refs": ["stat_1", "stat_2"],
  "related_recommendation_refs": ["rec_3"],
  "confidence": 0.0
}
```

### Component opportunities

- Key finding card
- Finding with evidence drawer
- Executive summary grid
- "What this means" module

---

## 1.2 Callout

### Definition

A visually or editorially emphasized block that interrupts or supplements main narrative flow.

### Common indicators

- Boxed text
- Different background color
- "Note," "Important," "Example," "Why it matters"
- Shorter than surrounding body text
- May contain a statistic, quote, definition, or warning

### Extract fields

```json
{
  "pattern": "callout",
  "callout_type": "why_it_matters",
  "title": "Why this matters",
  "body": "Local procurement connects public spending to regional economic impact.",
  "contained_patterns": ["claim_4", "stat_6"],
  "confidence": 0.0
}
```

### Component opportunities

- Sidebar box
- Inline emphasis panel
- Expandable aside
- Mobile card

---

## 1.3 Question

### Definition

A direct question posed to the reader, decision-maker, partner, or authoring team.

### Common indicators

- Ends with "?"
- Appears in checklist or planning section
- Often starts with "Have we," "Do we," "Are we," "What," "How"
- May have bold label before it

### Extract fields

```json
{
  "pattern": "question",
  "question_text": "Do we have support from organizational leadership?",
  "topic": "support and resources",
  "audience": "partnership team",
  "answer_expected": "yes_no_or_discussion",
  "confidence": 0.0
}
```

### Component opportunities

- Checklist item
- Self-assessment question
- FAQ item
- Planning worksheet

---

## 1.4 Answer

### Definition

A response to a question in a Q&A, FAQ, interview, or explainer format.

### Common indicators

- Follows a question
- Introduced by "Answer:", "A:", or a speaker label
- May be in accordion-like sections online
- Often paired with headings phrased as questions

### Extract fields

```json
{
  "pattern": "answer",
  "question_ref": "q_12",
  "answer_text": "Yes, but only if implementation responsibilities are clearly defined.",
  "confidence": 0.0
}
```

### Component opportunities

- FAQ accordion
- Q&A pair
- Explainer module

---

## 1.5 Example

### Definition

A concrete illustration of an abstract claim, recommendation, or pattern.

### Common indicators

- "For example," "such as," "in practice"
- Named place/program/organization
- May include a quote, mini-story, or outcome
- Often shorter than full case study

### Extract fields

```json
{
  "pattern": "example",
  "example_text": "In Oklahoma, local purchasing could generate an estimated $343 million in food system expenditure.",
  "related_claim_ref": "claim_2",
  "geography": "Oklahoma",
  "confidence": 0.0
}
```

### Component opportunities

- Example card
- Inline illustration
- "In practice" sidebar
- Map marker popup

---

## 1.6 Step

### Definition

One item in a process, stage, sequence, roadmap, or method.

### Common indicators

- Numbered stage/phase/step
- Verbs indicating action
- Headings like "Stage 4"
- Connected to other steps by sequence labels

### Extract fields

```json
{
  "pattern": "step",
  "sequence_number": 4,
  "title": "Partner and Implement Cross-Sector Solutions",
  "description": "Implement cross-sector work to make progress toward shared outcomes.",
  "subitems": ["question_1", "question_2"],
  "confidence": 0.0
}
```

### Component opportunities

- Process diagram
- Step card
- Roadmap
- Timeline
- Accordion stepper

---

# Layer 2: Compound structures

These are groups of content units with repeated shape or shared purpose.

## 2.1 List

### Definition

A set of related items, usually equal in hierarchy.

### Common indicators

- Bullets
- Numbering
- Repeated paragraph starts
- Repeated bold lead phrases
- Line breaks between short items

### Extract fields

```json
{
  "pattern": "list",
  "list_type": "benefits",
  "title": "Benefits to states",
  "items": [
    {"label": "Stable income", "description": "for small and mid-sized family farms"},
    {"label": "Job creation", "description": "across the food value chain"}
  ],
  "ordered": false,
  "confidence": 0.0
}
```

### Component opportunities

- Bullet list
- Icon list
- Card grid
- Numbered cards
- Benefit diagram

---

## 2.2 Checklist

### Definition

A list of questions, tasks, criteria, or requirements that can be evaluated item by item.

### Common indicators

- Checkmark icons
- Questions grouped under a heading
- "Have we," "Do we," "Are we"
- Repeated criterion labels

### Extract fields

```json
{
  "pattern": "checklist",
  "title": "Key questions to consider",
  "items": [
    {
      "label": "Community Impact",
      "question": "Will the partnership benefit the target population?"
    }
  ],
  "audience": "implementation team",
  "confidence": 0.0
}
```

### Component opportunities

- Checklist module
- Self-assessment worksheet
- Interactive completion tracker
- Criteria matrix

---

## 2.3 Q&A / FAQ

### Definition

A collection of question-answer pairs.

### Common indicators

- Repeated Q/A structure
- Headings phrased as questions
- "Frequently Asked Questions"
- Alternating speaker/interviewer text

### Extract fields

```json
{
  "pattern": "qa_set",
  "title": "Frequently Asked Questions",
  "pairs": [
    {
      "question": "What is Food is Medicine?",
      "answer": "Food is Medicine programs use food-based interventions to improve health outcomes."
    }
  ],
  "confidence": 0.0
}
```

### Component opportunities

- FAQ accordion
- Searchable Q&A
- Interview layout
- Expand/collapse explainer

---

## 2.4 Table of data

### Definition

Rows and columns containing structured values.

### Common indicators

- Grid lines or aligned columns
- Repeated row labels
- Header row
- Numeric values aligned vertically
- Tabular Word formatting

### Extract fields

```json
{
  "pattern": "data_table",
  "title": "Impact of locally sourced FIM on Oklahoma's farmers",
  "columns": [
    {"name": "Revenue for local farmers", "type": "currency"},
    {"name": "Number of small and mid-sized farms supported", "type": "count"}
  ],
  "rows": [
    ["$37,481,000", "270"]
  ],
  "source_notes": ["1"],
  "confidence": 0.0
}
```

### Component opportunities

- Styled table
- Stat cards
- Comparison chart
- Dashboard
- Filterable data table
- State/entity selector

---

## 2.5 Metric set

### Definition

A small group of related metrics that summarize a topic, place, program, or outcome.

### Common indicators

- 2-6 statistics near each other
- Shared geography/topic/time period
- Labels with values
- Often visually represented as cards

### Extract fields

```json
{
  "pattern": "metric_set",
  "subject": "Oklahoma FIM analysis",
  "metrics": [
    {"label": "Total population", "value": "4,095,000"},
    {"label": "FIM-eligible population", "value": "737,000"},
    {"label": "Annual FIM expenditure at scale", "value": "$867,994,000"}
  ],
  "geography": "Oklahoma",
  "time_period": "2026",
  "confidence": 0.0
}
```

### Component opportunities

- Stat card row
- Profile header
- Dashboard summary
- Comparison panel

---

## 2.6 Comparison

### Definition

A structure that compares two or more entities, options, time periods, populations, or scenarios.

### Common indicators

- "Compared with," "versus," "more/less than"
- Tables with multiple entities
- Before/after language
- Pros/cons
- State-by-state or group-by-group values

### Extract fields

```json
{
  "pattern": "comparison",
  "comparison_type": "geographic",
  "entities": ["California", "Oklahoma"],
  "metrics": ["population", "expenditure", "jobs"],
  "baseline": "national average",
  "confidence": 0.0
}
```

### Component opportunities

- Comparison table
- Bar chart
- Before/after module
- State selector
- Scenario toggle

---

## 2.7 Process / sequence

### Definition

A set of steps that happen in order.

### Common indicators

- "Stage," "Step," "Phase"
- Numbered headings
- Arrows, timelines, progress markers
- Phrases like "first," "next," "then," "finally"

### Extract fields

```json
{
  "pattern": "process",
  "title": "Partnership stages",
  "steps": [
    {"number": 1, "title": "Assess conditions"},
    {"number": 4, "title": "Implement cross-sector solutions"}
  ],
  "is_linear": true,
  "confidence": 0.0
}
```

### Component opportunities

- Timeline
- Stepper
- Process diagram
- Phase cards

---

## 2.8 Argument chain

### Definition

A linked sequence of claim → evidence → implication → recommendation.

### Common indicators

- Claim followed by data and policy implication
- Sections with "because," "therefore," "as a result"
- Recommendations tied to findings
- Executive summary logic

### Extract fields

```json
{
  "pattern": "argument_chain",
  "claim_ref": "claim_1",
  "evidence_refs": ["stat_1", "case_1"],
  "implication": "FIM procurement could support local farm revenue.",
  "recommendation_refs": ["rec_1"],
  "confidence": 0.0
}
```

### Component opportunities

- Evidence stack
- Finding-to-action module
- Policy argument card
- Executive summary narrative

---

# Layer 3: Page/section modules

These are recognizable page-level or section-level modules.

## 3.1 Case study

### Definition

A specific story or example showing how a program, policy, organization, or community operates in practice.

### Common indicators

- Named place/program/organization
- Context/problem/action/outcome structure
- Quotes or specific actors
- Boxed sidebar or standalone section
- Headings like "Case Study," "In Practice," "Community Spotlight"

### Extract fields

```json
{
  "pattern": "case_study",
  "title": "Oklahoma FIM implementation",
  "place": "Oklahoma",
  "organization_or_program": "Food is Medicine",
  "problem": "Need to connect local procurement with health and economic outcomes.",
  "intervention": "Statewide FIM expenditure model.",
  "outcomes": [
    {"metric": "Potential expenditure in local food system", "value": "$343,928,000"},
    {"metric": "Potential jobs created", "value": "5,040"}
  ],
  "quotes": [],
  "source_notes": ["1"],
  "confidence": 0.0
}
```

### Component opportunities

- Case study card
- Story page
- Map-linked profile
- Problem/intervention/outcome module

---

## 3.2 State / geography profile

### Definition

A structured profile for a place, usually with population, metrics, and impacts.

### Common indicators

- Large place name
- "State," "County," "Region"
- Date of analysis
- Metric summary
- Multiple impact metrics

### Extract fields

```json
{
  "pattern": "geography_profile",
  "geography_type": "state",
  "name": "Oklahoma",
  "date_of_analysis": "2026",
  "summary_metrics": [
    {"label": "Total population", "value": "4,095,000"},
    {"label": "FIM-eligible population", "value": "737,000"}
  ],
  "impact_metrics": [
    {"label": "Potential expenditure in local food system", "value": "$343,928,000"}
  ],
  "confidence": 0.0
}
```

### Component opportunities

- State profile page
- Interactive map detail panel
- Downloadable one-pager
- Compare-my-state selector

---

## 3.3 Explainer module

### Definition

A section that explains a concept, model, process, or field to readers.

### Common indicators

- Definitions and examples
- "What is..." headings
- Simple diagrams
- Plain-language explanatory paragraphs
- May precede technical sections

### Extract fields

```json
{
  "pattern": "explainer",
  "topic": "Food is Medicine",
  "definition_refs": ["def_1"],
  "examples": ["example_2"],
  "reader_question": "What is Food is Medicine?",
  "confidence": 0.0
}
```

### Component opportunities

- Explainer card
- Accordion
- Diagram
- "How it works" module

---

## 3.4 Executive summary

### Definition

A condensed section summarizing purpose, findings, recommendations, and evidence.

### Common indicators

- Heading "Executive Summary," "Summary," "Overview"
- Appears near beginning
- Contains key findings, recommendations, and high-level statistics
- Often more skimmable than body sections

### Extract fields

```json
{
  "pattern": "executive_summary",
  "purpose": "Analyze the potential impact of FIM programs.",
  "key_findings": ["finding_1", "finding_2"],
  "top_recommendations": ["rec_1", "rec_2"],
  "featured_metrics": ["stat_1", "stat_2"],
  "confidence": 0.0
}
```

### Component opportunities

- Summary landing section
- Key findings grid
- Executive brief PDF
- "Read this first" panel

---

## 3.5 Methodology section

### Definition

A section explaining how data, analysis, research, or estimates were produced.

### Common indicators

- Heading "Methodology," "Methods," "Data Sources," "Approach"
- Describes datasets, assumptions, formulas, limitations
- Often contains source notes, dates, and caveats

### Extract fields

```json
{
  "pattern": "methodology",
  "methods_summary": "Estimates are based on population analysis and expenditure assumptions.",
  "data_sources": ["source_1", "source_2"],
  "assumptions": ["assumption_1"],
  "limitations": ["limitation_1"],
  "confidence": 0.0
}
```

### Component opportunities

- Methodology accordion
- Data source panel
- Technical appendix
- Assumption table

---

## 3.6 Recommendation agenda

### Definition

A grouped set of recommended actions, often with actors, timelines, and rationale.

### Common indicators

- Heading "Recommendations," "Policy Agenda," "Next Steps"
- Multiple action-oriented items
- May be grouped by actor, timeframe, priority, or theme

### Extract fields

```json
{
  "pattern": "recommendation_agenda",
  "title": "Recommendations",
  "recommendations": ["rec_1", "rec_2"],
  "grouping": "theme",
  "actors": ["state agency", "community partners"],
  "confidence": 0.0
}
```

### Component opportunities

- Action agenda
- Priority matrix
- Actor-specific checklist
- Roadmap

---

# Layer 4: Publication sections

These are broad sections within a long-form publication.

## 4.1 Problem / context section

### Definition

A section that establishes the issue, stakes, background, or need.

### Indicators

- Background history
- Problem statements
- Baseline statistics
- "Why this matters"
- "Current conditions"

### Extract fields

```json
{
  "pattern": "problem_context_section",
  "problem_statement": "Existing procurement systems may not fully support local food economies.",
  "context_stats": ["stat_1", "stat_2"],
  "affected_populations": ["small and mid-sized family farms"],
  "confidence": 0.0
}
```

---

## 4.2 Findings section

### Definition

A section presenting analytical conclusions.

### Indicators

- Heading "Findings," "Results," "What We Found"
- Multiple key findings
- Evidence tied to each finding

### Extract fields

```json
{
  "pattern": "findings_section",
  "findings": ["finding_1", "finding_2", "finding_3"],
  "evidence_density": "high",
  "confidence": 0.0
}
```

---

## 4.3 Recommendations section

### Definition

A section telling readers what should happen next.

### Indicators

- Action verbs
- Stakeholders
- Timelines
- "Recommendations," "Next Steps," "Call to Action"

### Extract fields

```json
{
  "pattern": "recommendations_section",
  "agenda_ref": "agenda_1",
  "primary_audience": "policymakers",
  "confidence": 0.0
}
```

---

## 4.4 Data appendix

### Definition

A section containing detailed tables, formulas, assumptions, or supporting data.

### Indicators

- Many tables
- Detailed source notes
- Technical definitions
- "Appendix," "Supplemental Data"

### Extract fields

```json
{
  "pattern": "data_appendix",
  "tables": ["table_1", "table_2"],
  "source_notes": ["source_1"],
  "confidence": 0.0
}
```

---

# Layer 5: Whole-publication archetypes

These describe what the entire publication is trying to do.

## 5.1 Policy advocacy piece

### Definition

A publication arguing for policy change, funding, regulation, or public action.

### Indicators

- Problem statement
- Evidence and impacts
- Recommendations or asks
- Policymaker or public-sector audience
- Moral/economic/social rationale

### Extract fields

```json
{
  "pattern": "policy_advocacy_piece",
  "primary_issue": "Food is Medicine implementation",
  "desired_change": "statewide support and implementation",
  "target_audiences": ["state policymakers", "agency leaders", "advocates"],
  "argument_chains": ["arg_1", "arg_2"],
  "recommendations": ["rec_1", "rec_2"],
  "confidence": 0.0
}
```

### Publishing opportunities

- Digital report landing page
- Executive summary
- Action agenda
- Interactive data module
- Policymaker one-pager
- Companion designed PDF

---

## 5.2 Research report

### Definition

A publication presenting analysis, findings, methodology, and implications.

### Indicators

- Research questions
- Methods/data sources
- Findings
- Limitations
- Citations

### Extract fields

```json
{
  "pattern": "research_report",
  "research_questions": ["question_1"],
  "methodology_ref": "method_1",
  "findings": ["finding_1", "finding_2"],
  "limitations": ["limitation_1"],
  "confidence": 0.0
}
```

### Publishing opportunities

- Long-form web report
- Downloadable PDF
- Data appendix
- Findings explorer
- Citation/source panel

---

## 5.3 Toolkit / guide

### Definition

A practical publication that helps readers do something.

### Indicators

- Steps, checklists, worksheets
- "How to," "Guide," "Toolkit"
- Questions to consider
- Templates/resources

### Extract fields

```json
{
  "pattern": "toolkit_guide",
  "target_user": "cross-sector partnership teams",
  "tasks_supported": ["planning", "implementation", "evaluation"],
  "tools": ["checklist_1", "worksheet_1"],
  "confidence": 0.0
}
```

### Publishing opportunities

- Interactive toolkit
- Checklist modules
- Downloadable worksheets
- Step-by-step guide

---

## 5.4 Data profile / dashboard report

### Definition

A publication organized around metrics for places, entities, populations, or scenarios.

### Indicators

- Repeated profiles
- Metric sets
- Tables
- State/county/program pages
- Comparisons

### Extract fields

```json
{
  "pattern": "data_profile_report",
  "profile_subject_type": "state",
  "profiles": ["geo_profile_oklahoma"],
  "common_metrics": ["population", "eligible_population", "expenditure", "jobs"],
  "confidence": 0.0
}
```

### Publishing opportunities

- Interactive dashboard
- Profile pages
- Map
- State/entity selector
- Custom PDF export

---

## 5.5 Strategic plan

### Definition

A publication describing goals, priorities, actions, timelines, and success measures.

### Indicators

- Vision/mission/goals
- Priorities
- Action steps
- Timelines
- Metrics

### Extract fields

```json
{
  "pattern": "strategic_plan",
  "goals": ["goal_1", "goal_2"],
  "priorities": ["priority_1"],
  "actions": ["rec_1"],
  "timeline_refs": ["timeline_1"],
  "metrics": ["stat_1"],
  "confidence": 0.0
}
```

### Publishing opportunities

- Goals dashboard
- Roadmap
- Priority cards
- Progress tracker

---

# General recognition prompts

## Prompt A: Document-level pattern map

Use this when analyzing a whole document or a large section.

```text
You are analyzing a long-form public-interest publication for information design patterns.

Your task is not to rewrite the document. Your task is to identify reusable information structures that could become web or PDF components.

Return structured JSON only.

Identify:
1. Whole-publication archetype candidates.
2. Major section types.
3. Repeated content structures.
4. Designable structures such as metric sets, checklists, case studies, comparisons, processes, Q&A sets, recommendation agendas, and data profiles.
5. Places where the source supports a transformation now.
6. Places where a stronger digital treatment would require missing data or editorial decisions.

For each detected pattern, include:
- pattern name
- source location
- source text excerpt
- extracted fields
- confidence from 0 to 1
- why this pattern was detected
- suggested component treatments
- missing inputs, if any

Do not invent facts, categories, missing metrics, locations, quotes, or recommendations.
If a pattern is plausible but uncertain, mark it as tentative.
```

---

## Prompt B: Segment classifier

Use this on chunks, pages, or sections after initial extraction.

```text
Classify the following document segment into information patterns.

Look for patterns at multiple layers:
- atomic: statistic, quotation, claim, recommendation, entity, source note, definition, date/timeline marker
- unit: key finding, callout, question, answer, example, step
- compound: list, checklist, Q&A set, data table, metric set, comparison, process, argument chain
- module: case study, geography profile, explainer, executive summary, methodology, recommendation agenda

Return JSON with an array of detected patterns.

For each pattern:
- pattern
- layer
- confidence
- exact source text or table cells used
- extracted fields
- parent-child relationships
- component opportunities
- warnings about ambiguity

Do not rewrite or improve the source. Extract only what is present.
```

---

## Prompt C: Quote extractor

```text
Extract quotations and attributions from the supplied text.

A quotation may appear as:
- text inside quotation marks
- an indented or styled blockquote
- a sentence followed by an attribution line
- a paragraph introduced by a speaker name
- a quote embedded in a case study or sidebar

For each quote, return:
- quote_text
- speaker_name, if present
- speaker_title, if present
- speaker_affiliation, if present
- attribution_text exactly as written
- nearby topic or section heading
- whether it is suitable as a pull quote
- confidence

Rules:
- Do not treat scare quotes or quoted terms as quotations unless they are attributed speech.
- Do not invent speaker details.
- If attribution is nearby but uncertain, include it with lower confidence and explain why.
```

---

## Prompt D: Statistic extractor

```text
Extract statistics and quantitative claims from the supplied text or table.

For each statistic, return:
- value exactly as written
- normalized_value, if safe
- unit
- label
- geography, if present
- population/entity, if present
- time period, if present
- comparison or baseline, if present
- source note marker, if present
- surrounding claim
- confidence

Also identify whether each statistic is:
- standalone evidence
- part of a metric set
- part of a comparison
- part of a data table
- candidate for a stat card or chart

Do not calculate new values unless explicitly asked.
Do not infer missing units unless strongly implied by nearby labels.
```

---

## Prompt E: Table-to-component analyzer

```text
Analyze the supplied table for possible web-native treatments.

Return:
- table purpose
- row entities
- column metrics or attributes
- whether the table is primarily a comparison, metric set, profile, schedule, budget, recommendation matrix, or appendix data
- key values that deserve emphasis
- columns that are likely metadata/source notes
- whether the table should remain a table
- alternative component treatments

For each possible treatment, include:
- treatment name
- why it fits
- required fields
- fields already present
- missing fields
- accessibility risks
- confidence

Do not discard table structure. If recommending cards/charts, preserve a table fallback.
```

---

## Prompt F: Checklist/question-set extractor

```text
Detect whether the supplied segment is a checklist, question set, self-assessment, or planning worksheet.

Look for:
- repeated questions
- checkmark icons
- labels followed by questions
- yes/no or discussion prompts
- grouped criteria
- implementation/planning language

Return:
- title
- audience
- checklist type
- items with label, question text, description, and topic
- whether items are ordered or unordered
- suggested component treatments
- confidence

Do not convert statements into questions unless they are already phrased as prompts or criteria.
```

---

## Prompt G: Case study extractor

```text
Detect whether the supplied section is a case study, profile, example, or spotlight.

Extract:
- title
- place
- organization/program
- people or stakeholders
- problem/context
- intervention/action
- outcomes/results
- statistics
- quotes
- dates
- source notes
- related recommendations
- confidence

Classify the structure as:
- full case study
- short example
- geography profile
- program profile
- anecdote only

Do not invent missing outcomes or quotes.
If the section lacks problem/action/outcome structure, identify what is missing.
```

---

## Prompt H: Policy advocacy archetype detector

```text
Analyze whether this publication or section is making a policy advocacy argument.

Look for:
- public problem or need
- affected populations
- evidence of harm, opportunity, cost, or benefit
- policy recommendations or asks
- target decision-makers
- urgency or timeline
- call to action
- values framing

Return:
- advocacy issue
- desired change
- target audiences
- main claims
- supporting evidence
- recommendations
- implied theory of change
- missing evidence or missing decision-maker asks
- confidence

Do not intensify the advocacy language. Extract the argument as written.
```

---

# Pattern-to-component recommendation prompt

```text
Given the extracted information patterns below, recommend deterministic web/PDF component treatments.

For each pattern, return 1-5 component options.

Each option must include:
- component name
- information pattern it serves
- why it helps the reader
- required structured fields
- available fields
- missing fields
- content risks
- accessibility considerations
- whether the transformation is safe now or requires editorial review
- whether the component can be styled by an external design system

Do not recommend purely visual treatments unless they improve comprehension, comparison, trust, navigation, or action.
Do not invent content.
```

---

# Suggested deterministic rule shape

Avoid a pile of hard-coded if/else rules. Let patterns and components declare their own fit.

```json
{
  "component": "stat_card_grid",
  "accepts_patterns": ["metric_set"],
  "required_fields": ["metrics[].label", "metrics[].value"],
  "optional_fields": ["metrics[].unit", "metrics[].source_note_ref", "subject", "geography"],
  "fit_rules": [
    {"rule": "metric_count_between", "min": 2, "max": 6, "weight": 0.3},
    {"rule": "labels_short_enough", "max_chars": 70, "weight": 0.2},
    {"rule": "shared_subject_present", "weight": 0.2},
    {"rule": "values_are_numeric_or_currency", "weight": 0.2},
    {"rule": "source_notes_preserved", "weight": 0.1}
  ],
  "output_modes": ["html", "pdf"],
  "accessibility_requirements": [
    "visible labels",
    "source notes linked",
    "table fallback if derived from table"
  ]
}
```

---

# Open questions for RK3

1. Should pattern recognition be part of core conversion, or a separate enhancement pass?
2. Which patterns should be deterministic-only, and which can be LLM-assisted?
3. What confidence threshold should trigger automatic transformation versus editorial review?
4. What is the minimum IR schema needed to support these patterns without creating a new spaghetti layer?
5. How should RK3 preserve the original source structure when offering alternative treatments?
6. Should users be able to accept/reject pattern detections and feed those corrections back into future rules?
7. What is the first milestone pattern set?

Suggested first milestone:

```text
statistics
quotes
lists
checklists
data tables
metric sets
case studies
recommendation agendas
geography profiles
```

These appear often, are valuable, and map clearly to useful web/PDF components.
