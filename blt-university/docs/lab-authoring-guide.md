# Lab Authoring Guide

BLT University labs live in `_labs/` as Markdown files with YAML frontmatter. The frontmatter drives the lab listing page, lab detail page, and interactive lab engine.

Use [docs/lab-template.md](lab-template.md) as the starting point for new labs.

## Validation

Validate labs before opening a pull request:

```bash
python3 -m pip install python-frontmatter jsonschema
python3 scripts/validate_labs.py
```

The validator checks every `_labs/*.md` file against `schemas/lab.schema.json` and prints the exact field path for each error.

```text
FAILED: _labs/example.md
  - tasks.1.simulation.vulnerable_lines.0: 0 is less than the minimum of 1
```

## Lab Frontmatter

Every lab must include:

- `layout`: must be `lab`
- `title`: human-readable lab title
- `description`: short description shown on lab cards and lab pages
- `difficulty`: `beginner`, `intermediate`, or `advanced`
- `category`: broad category such as `Web Security`
- `estimated_time`: estimated completion time in minutes
- `tasks`: ordered list of lesson and simulation tasks

Optional proposal metadata is supported but not required yet:

- `owasp_category`: `A01` through `A10`
- `track`: `professional`, `hygiene`, or `both`
- `tags`: searchable labels
- `learning_objectives`: learner outcomes
- `success_criteria`: lab-level completion criteria
- `attack_payloads`: lab-level payload examples

## Task Structure

Current labs use this task shape:

```yaml
- name: Task Name
  description: Short task description.
  type: theory
  order: 1
```

The schema supports `theory`, `mcq`, and `simulation` task types.

### Theory Tasks

Theory tasks teach the concept with Markdown content. They usually include an embedded multiple-choice knowledge check.

```yaml
- name: Introduction to XSS
  description: Learn how XSS vulnerabilities happen.
  type: theory
  order: 1
  heading: What is XSS?
  content: |
    Explain the concept in Markdown.
  mcq:
    question: Which sink is risky for untrusted HTML?
    options:
      - A) textContent
      - B) innerHTML
      - C) appendChild with a trusted node
      - D) JSON.parse
    answer: B
```

### MCQ Tasks

Standalone `mcq` tasks are reserved for future use. For now, prefer embedding `mcq` inside a `theory` task because that is what the current lab layout renders.

### Simulation Tasks

Simulation tasks power the identify, explain, and fix flow.

```yaml
- name: Reflected XSS
  description: Practice fixing an unsafe HTML sink.
  type: simulation
  order: 2
  simulation:
    engine: xss-reflected
    type: reflected_xss
    scenario: vulnerable_blog
    target_url: /xss-lab/blog
    vulnerable_code: |
      const comment = request.query.comment;
      preview.innerHTML = comment;
    vulnerable_lines:
      - 2
    explain:
      question: Why does this payload execute?
      options:
        - id: unsafe_html_sink
          label: The app writes attacker-controlled HTML into the DOM.
        - id: missing_database
          label: The app does not use a database.
      answer: unsafe_html_sink
    expected_patterns:
      - safe_text_sink
      - output_encoding
    vulnerable_parameters:
      - comment
    success_payload: "<script>alert('XSS')</script>"
    success_criteria: JavaScript executes in the preview.
    fix_starter_code: |
      const comment = request.query.comment;
      preview.innerHTML = comment;
    hints:
      - Find where untrusted input reaches an HTML sink.
      - Use textContent or encode output before rendering.
```

The current schema validates known simulation fields and allows additional engine-specific fields. This keeps existing SQL injection, XSS, and CSRF labs valid while leaving room for IDOR, Broken Authentication, and future engines.

## Authoring Guidelines

- Keep all examples ethical and scoped to simulated or intentionally vulnerable targets.
- Use one-based `vulnerable_lines` that match the displayed `vulnerable_code`.
- Prefer clear defensive pattern names in `expected_patterns`, such as `parameterized_query`, `output_encoding`, `csrf_token`, or `authorization_check`.
- Make hints progressive: start broad, then point toward the fix.
- Use lowercase difficulty values for labs: `beginner`, `intermediate`, `advanced`.
- Keep simulation engine ids in kebab case so new engines can be grouped by prefix.

## Common Validation Fixes

- Missing `layout`: add `layout: lab`.
- `estimated_time` is a string: use `estimated_time: 45`, not `estimated_time: "45"`.
- Wrong task title field: current labs use `name`, not `title`.
- Standalone quiz does not render: embed `mcq` inside a `theory` task until the layout supports standalone `mcq` tasks.
- difficulty: 'beginer' is not one of ['beginner', 'intermediate', 'advanced']
