---
name: atrinik-github-governance
description: Publish Atrinik PRs, govern GitHub policy, or review and explicitly merge native PR stacks.
---

# Atrinik GitHub Governance

## Route and review the task

1. For native PR stack review or an explicitly authorized merge, read and
   follow [the stack contract](references/pr-stack-review-and-merge.md) in full;
   Review-only work is read-only and never grants merge authority.
2. For PR-only work, read its repository's `AGENTS.md`, use **Publish pull
   requests**, and skip steps 3–5.
3. For policy, settings, Actions, checks, or release governance, read the
   workspace guide and the current `README.md` and `AGENTS.md` of
   `atrinik/github-settings`, then compare them with the live GitHub API.
   Its publisher, audit and Project sync are retired. Never run its `bin/`
   scripts (`publish*`, `audit`, `sync-project` and the rest), with or without
   `--apply`, from its current tree, an old checkout or a release, even where
   its `README.md` or `AGENTS.md` still describes them.
4. Organization-wide rules live in organization rulesets aimed at all
   repositories, not lists of names; a required-check ruleset targets its one
   repository. Change a setting by hand under the owner's login only when the
   current task asks for that change; workflow dispatch also needs explicit
   authorization. Export each object before the change, re-read it live
   afterwards, and record the change in the same task where that `README.md`
   says records live. Never record a setting for later application.
5. Keep controls Team-plan compatible; document and review Enterprise-only
   migrations.

Use [shared read-only host auth](../../references/atrinik-workspace/docs/COORDINATOR_AUTH.md); verify actor
and task capabilities. Only the host changes login/scopes; API mutation gates remain.

## Optional commit-signing guidance

For optional SSH commit-signing setup and the host/container boundary, read
[the SSH signing reference](references/ssh-signing.md). It keeps personal
keys and signing configuration out of the repository and does not change
repository commit-signing policy.

## Change policy coherently

- When workflows change, update their permissions and dependency pins, and
  report any Actions allowlist, ruleset or required-check change they need;
  make it only if the task asks for it (step 4).
- Keep merge methods, semantic-release, Conventional Commit policy, visibility,
  default branches, and Codecov/OIDC policy consistent.
- Use least-privilege permissions and policy-required immutable action refs.
- Never print tokens or copy live secrets into configuration, logs, fixtures,
  commits, or review text.

## Publish pull requests

Titles use `type(optional-scope): concise description` by default; add `!` only
when a reviewer explicitly requests a breaking change, not automatically.
PR bodies must be substantive rendered GitHub-Flavored Markdown with actual
line breaks, never literal `\n` separators. Include `Summary`,
`Implementation / behavior`, `Validation`, and applicable
`Limitations / follow-up`; an issue-closing line alone is insufficient.
preserve contributor-authored text byte-for-byte, changing only a separately
delivery-owned section when authorized. Feed multi-section bodies by file/stdin.
After create/edit, inspect GitHub's rendered `bodyHTML`/`body_html`, not raw
body; verify headings, lists, inline code, issue-closing references, and
validation sections.

## Validate and hand off

For settings changes, check each changed object against a fresh live read.
For workflow changes, run actionlint, ShellCheck where shell changed, and
`git diff --check`. For PR-only work, run repository validation and the
rendered-view check.

For policy, document affected repositories, required checks, the pre-change
export used for rollback, and unchanged live state. For PRs, record remote
render verification. Use Conventional Commits.
