from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/atrinik-development"
SKILLS = PLUGIN / "skills"
DOCS = PLUGIN / "references/atrinik-workspace/docs"
LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def read_guidance_contract(path: Path) -> str:
    visited: set[Path] = set()

    def expand(current: Path) -> str:
        current = current.resolve()
        if current in visited:
            return ""
        visited.add(current)
        text = current.read_text(encoding="utf-8")
        references = []
        for target in LINK.findall(text):
            if "://" in target or target.startswith("#"):
                continue
            candidate = (current.parent / target.split("#", 1)[0]).resolve()
            if candidate.is_file() and candidate.is_relative_to(ROOT):
                references.append(expand(candidate))
        return "\n".join((text, *references))

    return expand(path)


def skill_frontmatter(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError(f"invalid frontmatter: {path}")
    block = text.split("---\n", 2)[1]
    values = {}
    for line in block.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip()
    name = values.get("name", "")
    description = values.get("description", "")
    if name != path.parent.name or not description:
        raise ValueError(f"invalid frontmatter: {path}")
    return name, description


class ImportedSkillContractTests(unittest.TestCase):
    def test_observation_recovery_has_distinct_prepublication_protocol(self) -> None:
            skill = SKILLS / "atrinik-issue-delivery"
            reference = "resource-observation-recovery.md"
            for path in (skill / "SKILL.md", skill / "references/preparation.md"):
                self.assertIn(reference, path.read_text())
            protocol = (skill / "references" / reference).read_text()
            for contract in ("correct-resource-observations-cas", "admit-in-progress-targets-cas",
                             "advance-retained-dependency-cas", "--retained-build-plan", "retained-runtime:PLAN_SHA256",
                             "`declare`", "`plan`", "`built`", "`topology`",
                             "target-refresh-cas", "revalidate-current-targets-cas",
                             "Candidate helpers are fixture-only", "byte-identical",
                             "JSON stdout", "configuration digest", "not a Docker verifier",
                             "generic external-runtime release/archive limitations"):
                with self.subTest(contract=contract):
                    self.assertIn(contract, protocol)
    
    def test_same_head_reconnect_uses_public_neutral_proof(self) -> None:
            issue = SKILLS / "atrinik-issue-delivery"
            project = SKILLS / "atrinik-project-delivery"
            for path in (
                issue / "references/preparation.md",
                issue / "references/delivery-ledger.md",
                project / "references/coordinator.md",
            ):
                with self.subTest(path=path):
                    self.assertIn("revalidate-current-targets-cas", path.read_text())
            protocol = (issue / "references/delivery-ledger.md").read_text()
            self.assertIn("--expected-generation GENERATION --expected-digest SHA256", protocol)
            self.assertNotIn("--expected-inode", protocol)
            self.assertIn("original generation/digest pair", protocol)
            self.assertIn("fresh actor and every target", protocol)
            self.assertIn("unmerged candidate helper", protocol)
            command_section = protocol.split("## Use the command surface", 1)[1].split("## ", 1)[0]
            self.assertIn("revalidate-current-targets-cas REVIEW_ROOT LEDGER_NAME", command_section)
            self.assertIn("[Revalidate every unchanged current target]", protocol)
    
    def test_content_issue_delivery_uses_main_as_sole_authored_source(self) -> None:
            content = " ".join(
                (
                    SKILLS / "atrinik-content-change/SKILL.md"
                ).read_text(encoding="utf-8").split()
            )
            delivery_root = SKILLS / "atrinik-issue-delivery"
            delivery = " ".join(
                read_guidance_contract(delivery_root / "SKILL.md").split()
            )
            report = (delivery_root / "assets/deep-review-report.md").read_text(
                encoding="utf-8"
            )
            checklist = (
                delivery_root / "references/deep-review-checklist.md"
            ).read_text(encoding="utf-8")
    
            for marker in {
                "`content@main` is the sole authored source",
                "select the target-specific publisher",
                "never edit, recreate, or create a PR against the former `1.x` line",
                "Classic-target artifact generated from it",
            }:
                with self.subTest(surface="content", marker=marker):
                    self.assertIn(marker, content)
            for marker in {
                "author only on `main`",
                "validate every affected target and consumer",
                "former `1.x` branch no longer exists as a live delivery target",
                "request a backport there",
                "A content `main` PR may close an explicitly selected issue",
            }:
                with self.subTest(surface="delivery", marker=marker):
                    self.assertIn(marker, delivery)
            self.assertIn("## Reviewed revision", report)
            self.assertIn("issues remain open", report)
            self.assertIn("independent final integrated review", checklist)
            self.assertIn("Missing or timed-out checks are not success", checklist)
    
    def test_program_master_publication_ledger_is_fail_closed(self) -> None:
            skill = SKILLS / "atrinik-program-delivery"
            body = " ".join(
                read_guidance_contract(skill / "SKILL.md").split()
            )
            ledger = " ".join(
                (skill / "references/master-publication-ledger.md")
                .read_text(encoding="utf-8")
                .split()
            )
            report = (skill / "assets/program-delivery-report.md").read_text(
                encoding="utf-8"
            )
            checklist = " ".join(
                (skill / "references/program-review-checklist.md")
                .read_text(encoding="utf-8")
                .split()
            )
            interface = " ".join(
                (skill / "agents/openai.yaml").read_text(encoding="utf-8").split()
            )
    
            for marker in {
                "<coordinate-sha256>.ledger.json",
                "GitHub linkage, marker text, the report, a leaf ledger",
                "Never adopt live text, an issue, a relationship, or a marker",
                "<coordinate-sha256>.publication.lock",
                "goal-specific locks are forbidden",
                "Path replacement stops the writer",
                "lock on the replaceable JSON path is invalid",
                "schema_version: 1",
                "goal_thread_id",
                "exact UTF-8 objective returned by the goal API",
                "contiguous integers from 1",
                "ordinary leaf progress does not rekey it",
                "next_ordered_graph: null | [graph_entry]",
                "json.dumps(value, ensure_ascii=False",
                "<!-- atrinik-program-delivery:v1 sha256=<64 lowercase hex> -->",
                "final line of `intended_body`",
                "record the canonical destination path as `self`",
                "at most 100 pages",
                "16 MiB total body bytes",
                "incomplete pagination and stops",
                "two consecutive complete scans",
                "newly visible exact result",
                "## Ordered-graph same-node rekey",
                "Graph changes never create a new comment",
                "`next_authority`/`next_ordered_graph`",
                "interruption must never permit POST",
                "one proposed missing-child publication",
                "zero occurrences of the",
                "## Missing-child creation and native linking",
                "never create again",
                "never link again",
                "ProgramLedgerModelTests",
                "GitHub exposes no relationship node ID",
                "atrinik-program-child",
                "proposal's recorded position",
                "pre_call_issue_node_ids",
                "pre_call_subissue_node_ids",
                "never accept a caller-supplied digest label",
            }:
                with self.subTest(marker=marker):
                    self.assertIn(marker, ledger)
    
            self.assertIn("references/master-publication-ledger.md", body)
            self.assertIn("before master-comment or missing-child mutation", body)
            self.assertLess(
                ledger.index("persist `planned` with exact intended body"),
                ledger.index("persist `in-flight` before the first POST"),
            )
            self.assertLess(
                ledger.index("persist `in-flight` before the first POST"),
                ledger.index("Call once"),
            )
            for marker in {
                "## Machine ledger mirror (evidence only)",
                "Canonical ledger path:",
                "Repository/master coordinate SHA-256:",
                "Goal authority / exact objective SHA-256:",
                "Remote comment node ID:",
                "## Leaf ledger composition",
                "Final master-comment generation / node / body digests:",
                "never authorizes publication",
                "Stable lock canonical path:",
                "Current / next authority and graph-rekey phase:",
                "Child create phase / intent digest / issue number / node / URL:",
                "Native link phase / intent digest / parent-child proof digest:",
            }:
                self.assertIn(marker, report)
            for marker in {
                "Master publication recovery",
                "generation/digest CAS",
                "complete bounded comment pagination",
                "accepted-but-not-yet-visible result",
                "ledger/report loss",
                "without live GitHub mutation",
                "cannot authorize or recover a write",
                "stable non-replaced lock file",
                "ordered-graph same-node rekeying",
                "summaries remain local",
                "separate create/link state slots",
            }:
                self.assertIn(marker, checklist)
            self.assertIn("machine-readable program ledger", interface)
            self.assertIn(
                "Without durable goal authority, keep summaries and proposed children local",
                body,
            )
            self.assertIn("create no master ledger, master comment, child, or link", body)
            self.assertIn("Publish the master summary only through", body)
    
    def test_native_pr_stack_governance_is_guarded_and_complete(self) -> None:
            skill = SKILLS / "atrinik-github-governance"
            package = {
                path.relative_to(skill).as_posix()
                for path in skill.rglob("*")
                if path.is_file()
            }
            self.assertEqual(
                package,
                {
                    "SKILL.md",
                    "agents/openai.yaml",
                    "references/pr-stack-review-and-merge.md",
                    "references/ssh-signing.md",
                },
            )
    
            body = read_guidance_contract(skill / "SKILL.md")
            interface = (skill / "agents/openai.yaml").read_text(encoding="utf-8")
            reference = (
                skill / "references/pr-stack-review-and-merge.md"
            ).read_text(encoding="utf-8")
            normalized = " ".join(reference.split())
    
            _, description = skill_frontmatter(skill / "SKILL.md")
            self.assertIn("review and explicitly merge native PR stacks", description)
            self.assertIn("references/pr-stack-review-and-merge.md", body)
            self.assertIn("Review-only work is read-only", body)
            self.assertIn("skip steps 3–6", body)
            self.assertNotIn("skip steps 2–5", body)
            self.assertIn("review a native PR stack", interface)
            self.assertIn("explicit user authority", interface)
    
            for marker in {
                "X-GitHub-Api-Version: 2026-03-10",
                "GET /repos/{owner}/{repo}/stacks?pull_request={number}",
                "GET /repos/{owner}/{repo}/stacks/{stack_number}",
                "Never infer membership from branch names",
                "same-repository linear dependency chains",
                "keep independent pull requests independent",
                "[Establish the exact native PR stack](#establish-the-exact-native-pr-stack)",
                "[Freeze and review both views](#freeze-and-review-both-views)",
                "[Require exact merge authority and current preflight](#require-exact-merge-authority-and-current-preflight)",
                "[Execute the guarded native atomic operation](#execute-the-guarded-native-atomic-operation)",
                "[Verify the result and preserve remaining work](#verify-the-result-and-preserve-remaining-work)",
                "[Read-only forward fixture](#read-only-forward-fixture)",
                "Define the selected portion as every position through the named top PR",
                "contiguous already-merged lower prefix",
                "every later selected layer must be open",
                "Reverify each prefix member's `merged_at`",
                "closed, reordered, missing, or inconsistent prefix",
                "The active suffix is the mutation scope",
                "With no merged prefix",
                "position 1 must target the frozen current trunk branch/SHA",
                "With a merged prefix, verify it from merge-result ancestry",
                "first active-suffix PR to target the frozen current trunk branch/SHA",
                "only each later active PR to base on the preceding active head",
                "cannot list unknown requests",
                "parent-to-head incremental diff",
                "trunk-to-selected-top cumulative diff",
                "deep-review checklist",
                "integration checklist",
                "Any push, rebase, retarget, membership change, lower-layer merge",
                "every required and applicable check exists and passes",
                "no self-approval is used",
                "actionable review conversation is resolved",
                "skipped-but-required",
                "GitHub CLI 2.97.0",
                "`github/gh-stack` v0.1.0",
                "does not send the asynchronous API's `sha` field",
                "repos/OWNER/REPOSITORY/pulls/TOP_PR/merge-async",
                "gh api --include --method PUT",
                "-f sha=REVIEWED_TOP_HEAD_SHA",
                "-f merge_method=squash",
                "-f merge_action=direct_merge",
                "`202 pending`",
                "`409` existing request",
                "Immediate `200 merged` or `200 enqueued`, or `400 failed`",
                "requested method/action/head",
                "Explicitly record a UUID as unavailable",
                "never invent absent response fields",
                "`403`, `404`, or `422`",
                "Do not resubmit without renewed authority, review, and preflight",
                "fixed upper bound",
                "gh api --include",
                "repos/OWNER/REPOSITORY/pulls/TOP_PR/merge-async/UUID",
                "separate the HTTP status from the body status",
                "For every poll, likewise separate and retain the included HTTP status",
                "body-level `pending` returned under polling HTTP `200`",
                "A timeout, transport loss, malformed response",
                "polling `403`, `404`, an expired result",
                "any unexpected non-`200` polling response",
                "whatever stack, selected and remaining PR, target ref/history",
                "stop with the UUID and exact response in a recovery handoff",
                "any later mutation requires refreshed authority, review, and preflight",
                "full authority, review, and preflight contract is refreshed",
                "Never emulate atomic merge with sequential `gh pr merge`",
                "For a partial-stack merge",
                "the previously merged prefix remains unchanged",
                "exactly the active suffix merged",
                "no unselected upper layer merged",
                "For every attempted operation, record in the handoff its HTTP status",
                "returned UUID or option fields only when supplied",
                "explicitly mark absent server fields unavailable",
                "For every terminal operation also record stack number and trunk",
                "stack number and trunk",
                "every selected PR's reviewed base/head and resulting squash SHA",
                "final target branch and tip",
                "Never call a merge endpoint in a forward test",
            }:
                with self.subTest(marker=marker):
                    self.assertIn(marker, normalized)
    
            self.assertEqual(reference.count("gh api --include"), 2)
    
            for prohibited in {
                "Never force-push",
                "bypass or relax rules",
                "enable auto-merge",
                "close issues manually",
                "apply cleanup",
                "blindly resubmit",
            }:
                with self.subTest(prohibited=prohibited):
                    self.assertIn(prohibited, normalized)
    
            self.assertIn(
                "Merge-ready handoffs from issue or program delivery are inputs",
                normalized,
            )
            self.assertNotIn("stacked pull request", reference.lower())
            terminology = "\n".join(
                path.read_text(encoding="utf-8")
                for path in {
                    skill / "SKILL.md",
                    skill / "agents/openai.yaml",
                    skill / "references/pr-stack-review-and-merge.md",
                }
            )
            self.assertNotIn("PR-stack", terminology)
            self.assertIn(
                "During every standalone PR stack review phase",
                normalized,
            )
            self.assertIn("including review under an explicit merge request", normalized)
            self.assertIn("do not create or update any report or other file", normalized)
            self.assertIn("Only a separately write-authorized delivery", normalized)
            self.assertIn(
                "In every standalone PR stack review phase, reuse only their review",
                normalized,
            )
            self.assertIn(
                "this contract overrides the deep-review checklist's report-instantiation",
                normalized,
            )
            self.assertIn("Keep that evidence in memory and the response", normalized)
            issue_delivery = (
                SKILLS / "atrinik-issue-delivery/SKILL.md"
            ).read_text(encoding="utf-8")
            authority_corpus = issue_delivery + (
                DOCS / "WINDOWS_GPU_PREFLIGHT.md"
            ).read_text(encoding="utf-8")
            program_delivery = (
                SKILLS / "atrinik-program-delivery/SKILL.md"
            ).read_text(encoding="utf-8")
            self.assertIn("It does not authorize", authority_corpus)
            self.assertRegex(issue_delivery, r"\bmerges?\b")
            self.assertIn("Do not infer merge authority", program_delivery)
            self.assertNotIn("merge-async", issue_delivery)
            self.assertNotIn("merge-async", program_delivery)
    
    def test_retained_recovery_and_helper_certification_remain_specialized(self) -> None:
            skill = SKILLS / "atrinik-issue-delivery"
            recovery = (skill / "references/resource-observation-recovery.md").read_text(encoding="utf-8")
            certification = (skill / "references/helper-lifecycle-review.md").read_text(encoding="utf-8")
            checklist = (skill / "references/deep-review-checklist.md").read_text(encoding="utf-8")
    
            for invariant in {
                "correct-resource-observations-cas",
                "admit-in-progress-targets-cas",
                "advance-retained-dependency-cas",
                "Candidate helpers are fixture-only",
                "revalidate-current-targets-cas",
            }:
                self.assertIn(invariant, recovery)
            for invariant in {
                "strict schema parsing",
                "generation/digest CAS",
                "contributor-section/outside-byte ownership",
                "missing, duplicated, reordered",
            }:
                self.assertIn(invariant, certification)
            self.assertIn("independent final integrated review", checklist)
    
    def test_program_and_project_entries_route_source_and_bound_leaves(self) -> None:
            program = SKILLS / "atrinik-program-delivery/SKILL.md"
            project = SKILLS / "atrinik-project-delivery/SKILL.md"
            program_text = program.read_text(encoding="utf-8")
            project_text = project.read_text(encoding="utf-8")
            normalized_program = " ".join(program_text.split())
    
            self.assertIn("../atrinik-issue-delivery/SKILL.md", LINK.findall(program_text))
            for invariant in {
                "explicit issue mode for every leaf",
                "never delegates PR-mode adoption",
                "Do not merge or close anything",
                "cumulative program review",
            }:
                self.assertIn(invariant, normalized_program)
            self.assertIn("../../references/atrinik-workspace/docs/SOURCE_DELIVERY.md", LINK.findall(project_text))
            self.assertIn("existing bound issue/PR delivery", project_text)
            self.assertIn("independent final review", project_text)
    
    

if __name__ == "__main__":
    unittest.main()
