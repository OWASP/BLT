#!/usr/bin/env node
// Labels and welcomes enrollment requests and course submissions.
//   node scripts/actions/welcome.mjs enrollment   (.forkmesh/blt-university--enrollment.yml)
//   node scripts/actions/welcome.mjs course       (.forkmesh/blt-university--course-submission.yml)
// Ported from the GitHub workflows enrollment.yml and course-submission.yml.
import { fileURLToPath } from "node:url";
import { readEvent, comment, changeLabels, labelNames, authorLogin, run } from "../../../scripts/actions/forge.mjs";

const PROJECT_URL = process.env.PROJECT_URL || "https://git.owaspblt.org/BLT/BLT-University";

export const MODES = {
  enrollment: {
    required: ["enrollment", "student"],
    review: ["under-review"],
    message: (user) => `👋 Welcome to BLT University, @${user}!

Thank you for your enrollment request. Our team will review your application and respond within 2-3 business days.

In the meantime:
- 🌟 Star this repository to stay updated
- 📖 Review the [course materials](${PROJECT_URL}/tree/main/_courses)
- 💬 Join our [Discussions](${PROJECT_URL}/discussions)
- 📚 Read our [Contributing Guide](${PROJECT_URL}/blob/main/contributing.html)

We're excited to have you join our community! 🎓`,
  },
  course: {
    required: ["course-submission", "instructor"],
    review: ["under-review", "instructor-application"],
    message: (user) => `🎓 Thank you for your course submission, @${user}!

We're excited to review your course proposal. Here's what happens next:

## Review Process

1. **Initial Review (3-5 days)**: Our curriculum team will review your proposal
2. **Feedback Round**: We may request clarifications or suggest improvements
3. **Approval**: Once approved, you'll be guided through the course creation process
4. **Publishing**: Your course will be added to the BLT University catalog

## Next Steps

While you wait:
- 📝 Start preparing your course materials
- 🔍 Review existing courses for format reference
- 📖 Read our [Instructor Guide](${PROJECT_URL}/blob/main/contributing.html)
- 💬 Join our instructor discussions

## Resources for Instructors

- [Course Template](${PROJECT_URL}/tree/main/_courses)
- [Style Guide](${PROJECT_URL}/blob/main/CONTRIBUTING.md)
- [Instructor Handbook](${PROJECT_URL}/wiki/Instructor-Handbook)

Thank you for contributing to open-source security education! 🌟`,
  },
};

/** Labels to add: the missing required ones plus the review labels. */
export function labelsToAdd(mode, current) {
  const { required, review } = MODES[mode];
  return [...new Set([...required, ...review])].filter((l) => !current.includes(l));
}

async function main() {
  const mode = process.argv[2];
  if (!MODES[mode]) throw new Error(`usage: welcome.mjs ${Object.keys(MODES).join("|")}`);
  const issue = readEvent().issue;
  if (!issue) throw new Error("no issue in the event payload");
  const add = labelsToAdd(mode, labelNames(issue));
  if (add.length) await changeLabels(issue.number, { add });
  await comment(issue.number, MODES[mode].message(authorLogin(issue)));
  if (mode === "course") console.log("Course submission received and will be reviewed by the curriculum team");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) run(main);
