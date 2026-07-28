import logging

from blt_mcp.server_base import _fetch, mcp

logger = logging.getLogger("blt-mcp.prompts")


@mcp.prompt(
    name="triage_vulnerability",
    description="Guide security vulnerability analysis with severity assessment, impact analysis, and recommendations.",
)
async def triage_vulnerability(
    vulnerability_description: str, affected_component: str
) -> list[dict]:
    """
    Generate a structured triage workflow for a security vulnerability.

    Args:
        vulnerability_description: Detailed description of the vulnerability.
        affected_component: The system component affected (e.g., "login form", "API gateway").
    """
    return [
        {
            "role": "user",
            "content": f"""You are a senior security analyst performing vulnerability triage for OWASP BLT.

## Vulnerability Report
**Affected Component:** {affected_component}
**Description:** {vulnerability_description}

## Triage Checklist
Please analyze this vulnerability and provide:

1. **Severity Assessment** (Critical / High / Medium / Low / Informational)
   - CVSS v3.1 base score estimate
   - Attack vector, complexity, and required privileges

2. **Impact Analysis**
   - Confidentiality, Integrity, Availability impact
   - Scope of affected users/data
   - Business impact assessment

3. **Exploitability**
   - Is a proof-of-concept available or trivially constructable?
   - Are there known exploits in the wild?

4. **Recommendations**
   - Immediate mitigation steps
   - Long-term remediation approach
   - Suggested BLT issue status (open, in_progress, wont_fix)
   - Recommended labels and assignee type

5. **Bacon Points Suggestion**
   - Recommended bacon points for the reporter based on severity and quality""",
        }
    ]


@mcp.prompt(
    name="plan_remediation",
    description="Create a comprehensive remediation plan for a security issue, including root cause analysis, fix steps, testing, and prevention.",
)
async def plan_remediation(issue_id: str, context: str = "") -> list[dict]:
    """
    Generate a step-by-step remediation plan for a BLT issue.

    Args:
        issue_id: The BLT issue ID to create a remediation plan for.
        context: Optional additional context about the environment or constraints.
    """
    # Attempt to fetch issue details from the API
    issue_details = ""
    try:
        raw = await _fetch(f"/bugs/{issue_id}", context="remediation plan")
        issue_details = f"\n## Issue Data (from BLT API)\n```json\n{raw}\n```"
    except Exception:
        issue_details = f"\n> Could not fetch issue {issue_id} from API. Proceed with the context provided."

    extra_context = f"\n## Additional Context\n{context}" if context else ""

    return [
        {
            "role": "user",
            "content": f"""You are a security engineer creating a remediation plan for OWASP BLT issue #{issue_id}.
{issue_details}
{extra_context}

Please provide a comprehensive remediation plan with the following sections:

1. **Root Cause Analysis**
   - What is the underlying technical cause?
   - What coding pattern or configuration led to this?

2. **Remediation Steps**
   - Step-by-step instructions to fix the vulnerability
   - Code changes required (with examples where possible)
   - Configuration changes needed

3. **Testing Plan**
   - How to verify the fix works
   - Regression tests to add
   - Edge cases to cover

4. **Prevention**
   - How to prevent similar issues in the future
   - Recommended linting rules, CI checks, or code review guidelines
   - Security training recommendations""",
        }
    ]


@mcp.prompt(
    name="review_contribution",
    description="Evaluate a contribution with quality assessment, strengths, improvements, and bacon point recommendations.",
)
async def review_contribution(
    contribution_id: str, contribution_type: str = "bug_report"
) -> list[dict]:
    """
    Generate a quality assessment for a BLT contribution.

    Args:
        contribution_id: The ID of the contribution (issue ID, comment ID, etc.).
        contribution_type: Type of contribution: "bug_report", "fix", "comment", or "triage".
    """
    # Attempt to fetch contribution details
    contribution_data = ""
    if contribution_type in ("bug_report", "fix"):
        try:
            raw = await _fetch(
                f"/bugs/{contribution_id}", context="contribution review"
            )
            contribution_data = f"\n## Contribution Data\n```json\n{raw}\n```"
        except Exception:
            contribution_data = f"\n> Could not fetch contribution {contribution_id}."

    return [
        {
            "role": "user",
            "content": f"""You are a senior reviewer evaluating a contribution to the OWASP BLT project.

**Contribution ID:** {contribution_id}
**Contribution Type:** {contribution_type}
{contribution_data}

Please evaluate this contribution and provide:

1. **Quality Assessment** (Excellent / Good / Needs Improvement / Insufficient)
   - Clarity and completeness of the report/fix
   - Reproducibility (for bug reports)
   - Technical accuracy

2. **Strengths**
   - What was done well?
   - Notable effort or thoroughness

3. **Areas for Improvement**
   - What could be improved?
   - Missing information or steps

4. **Bacon Points Recommendation**
   - Suggested bacon points (0-100 scale)
   - Justification based on:
     * Severity of the finding
     * Quality of the report
     * Effort demonstrated
     * Impact on the project""",
        }
    ]
