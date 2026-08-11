---
name: codebase-analysis-reporting
description: "Use when reporting full codebase architecture and risk."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [codebase-analysis, architecture-review, security-review, maintainability, reporting]
    related_skills: [codebase-inspection, technical-mentorship-workflow, systematic-debugging]
---

# Codebase Analysis Reporting

Use this skill when Tutu asks to analyze a repository/codebase and produce a comprehensive report, especially when the request is broader than line counts or a narrow code review.

The goal is to deliver a grounded engineering assessment: architecture, stack, code organization, runtime verification, security/privacy risks, test/deployment readiness, and prioritized next actions.

## Operating Standard

Do not produce a report from README claims alone. Treat documentation as a hypothesis and verify it against actual source files and runnable commands where possible.

A good report separates:

- What the system intends to be.
- What the code currently implements.
- What is scaffold/mock/prototype behavior.
- What blocks MVP or production use.

For Tutu, be direct and practical: identify the foundations to stabilize before recommending more features.

## Workflow

1. **Discover repository shape**
   - List files and identify subprojects.
   - Read README files, package/build files, manifests, and docs.
   - Check git branch/status/remotes/recent commits.
   - Note whether the repo is clean before and after analysis.

2. **Collect size and composition metrics**
   - Use `codebase-inspection`/pygount or a small deterministic counter.
   - Exclude dependency/build folders: `.git`, `node_modules`, `.gradle`, `build`, `dist`, `.venv`, `venv`, `.cache`, `coverage`.
   - Include top largest source files; they usually reveal coupling and maintainability hotspots.

3. **Read core boundaries**
   Inspect entry points and architectural seams, such as:
   - frontend app/root/router files;
   - backend server/app/routes/controllers;
   - mobile main activity/navigation/viewmodels;
   - dependency injection/config modules;
   - database schemas/repositories;
   - API clients/DTOs;
   - background workers/jobs/queues;
   - storage/cache/email abstractions;
   - security/auth middleware.

4. **Compare contracts across layers**
   Cross-check backend routes, frontend clients, mobile clients, and docs. Explicitly flag:
   - snake_case vs camelCase mismatches;
   - duplicated URL prefixes;
   - DTO field names that do not line up;
   - docs describing tests/features that are not present;
   - response shapes that clients cannot deserialize;
   - mocked or hardcoded identities hidden behind realistic UI.

5. **Run verification commands**
   Where safe and available:
   - install dependencies if necessary;
   - run type checks/lints;
   - run builds;
   - run tests;
   - run dependency audit/security checks;
   - start the service briefly and hit health/core endpoints.

   If a toolchain is missing, report the blocker honestly, but do not encode environment-specific failures as durable constraints.

6. **Assess production readiness**
   Cover at least:
   - authentication and authorization;
   - password/token handling;
   - secure randomness;
   - admin route protection;
   - upload/file handling;
   - persistence/durability;
   - schema migrations;
   - logging of sensitive data;
   - privacy/PII/GPS handling;
   - tests and CI;
   - deployment/config validation;
   - observability.

7. **Prioritize findings**
   Use severity tiers:
   - P0: blocks real deployment or creates serious security/data-integrity risk.
   - P1: blocks MVP quality, maintainability, or reliable operation.
   - P2: polish, optimization, and long-term improvements.

8. **Leave the working tree clean**
   If analysis changes lockfiles, generated outputs, caches, or build artifacts and the user did not ask for modifications, revert or clean them before finalizing.

## Report Shape

A comprehensive report should usually include:

1. short verdict;
2. verified context and commands run;
3. repository structure;
4. product purpose/domain model;
5. stack summary;
6. architecture summary;
7. subsystem-by-subsystem analysis;
8. security/privacy findings;
9. testing/build/deployment findings;
10. prioritized risks;
11. recommended next tasks;
12. practical assessment: prototype vs MVP vs production.

Keep the report readable in terminal output: simple headings, concise paragraphs, and direct recommendations.

## Pitfalls

- Do not confuse a polished dashboard with production readiness.
- Do not trust labels like "production-ready" until auth, persistence, tests, and deployment paths are verified.
- Do not ignore client/server contract drift; it is often the real blocker in multi-client systems.
- Do not preserve accidental changes from dependency installs/builds unless the user requested modifications.
- Do not turn missing local tools into long-term skill rules. Report the blocker for this run only.

## References

- `references/comprehensive-codebase-report-ghalingo.md` — compact checklist and findings pattern from a React/Express + Android speech-collection codebase audit.
