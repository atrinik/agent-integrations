from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from tests.test_imported_skill_contracts import (
    LINK,
    read_guidance_contract,
    skill_frontmatter,
)


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/atrinik-development"
SKILLS = PLUGIN / "skills"
DOCS = PLUGIN / "references/atrinik-workspace/docs"


class MigratedMixedContractTests(unittest.TestCase):
    def test_optional_process_diagnostics_are_guided(self) -> None:
            for path in (
                SKILLS / "atrinik-multi-repo-workspace/SKILL.md",
            ):
                with self.subTest(path=path):
                    text = " ".join(path.read_text(encoding="utf-8").split()).lower()
                    self.assertRegex(text, r"optional|discretionary")
                    self.assertIn("./atrinik agent-ledger update", text)
                    self.assertNotIn("process improvements added: none", text)
                    self.assertNotIn("tooling issues: none", text)
    
    def test_native_development_guidance_preserves_authority_boundaries(self) -> None:
            paths = [
                SKILLS / "atrinik-issue-delivery/SKILL.md",
            ]
            for path in paths:
                text = read_guidance_contract(path)
                normalized = " ".join(text.split())
                with self.subTest(path=path.relative_to(ROOT)):
                    self.assertIn("native", normalized.lower())
                    self.assertIn("worktree", normalized)
                    self.assertIn("pinned", normalized)
                    self.assertIn("ledger", normalized)
                    self.assertIn("leases", normalized)
                    self.assertRegex(
                        normalized,
                        r"Codex (?:never|must never) (?:launches|launch|launch or controls)"
                        r"[^.]{0,100}VS Code",
                    )
                    self.assertIn("GUI automation", normalized)
            execution = (DOCS / "LINUX_EXECUTION.md").read_text()
            compatibility = execution.split("## Existing bound container compatibility", 1)[1].split("\n## ", 1)[0]
            for gate in ("authenticated actor", "complete inventory", "clean",
                         "public CAS", "ordered leases", "30 minutes/12 hours",
                         "replace, remount, transfer or adopt"):
                self.assertIn(gate, " ".join(compatibility.split()))
            self.assertIn("runtime markers never authorize", read_guidance_contract(paths[-1]))
    
    def test_native_windows_gpu_handoff_is_synchronized(self) -> None:
            handoff = DOCS / "WINDOWS_GPU_PREFLIGHT.md"
            self.assertTrue(handoff.is_file())
            handoff_text = handoff.read_text(encoding="utf-8")
            for marker in {
                "native-windows-classic-gpu-preflight",
                "native-package-smoke",
                "d3d12-benchmark",
                "linux-only-coordinator",
                "ATRINIK_GPU_CONFORMANCE_DRIVER",
                "scripts/validate_windows_gpu_evidence.py",
            }:
                with self.subTest(marker=marker):
                    self.assertIn(marker, handoff_text)
    
            for path in {
                SKILLS / "atrinik-multi-repo-workspace/SKILL.md",
            }:
                with self.subTest(path=path.relative_to(ROOT)):
                    self.assertIn("WINDOWS_GPU_PREFLIGHT.md", path.read_text(encoding="utf-8"))
    
    def test_container_launch_recipes_are_build_or_runtime_scoped(self) -> None:
            paths = []
            paths.extend(sorted(DOCS.glob("*.md")))
            paths.extend(sorted((SKILLS / "").glob("*/SKILL.md")))
            paths.extend(sorted((SKILLS / "").glob("*/references/*.md")))
            allowed_configs = (
                ".devcontainer/server-runtime.json",
                ".devcontainer/windows-cross/devcontainer.json",
            )
            for path in paths:
                # Qualification is immutable historical evidence, not a current recipe.
                if path.name == "NATIVE_LINUX_QUALIFICATION.md":
                    continue
                text = path.read_text(encoding="utf-8")
                blocks = re.findall(r"(?:```|~~~)[^\n]*\n(.*?)(?:```|~~~)", text, re.DOTALL)
                for block in blocks:
                    commands = block.replace("\\\n", " ")
                    for line in commands.splitlines():
                        if re.match(r"\s*devcontainer\s+(?:up|exec)\b", line):
                            with self.subTest(path=path.relative_to(ROOT), command=line):
                                self.assertTrue(any(config in line for config in allowed_configs))
                        with self.subTest(path=path.relative_to(ROOT), command=line):
                            self.assertNotRegex(line, r"^\s*(?:code(?:\.cmd)?\b|vscode://|(?:xdotool|ydotool|osascript|wmctrl)\b)")
                with self.subTest(path=path.relative_to(ROOT)):
                    self.assertNotIn("Dev Containers: Reopen in Container", text)
                    self.assertNotIn("Dev Containers: Rebuild Container", text)
            auth = (DOCS / "COORDINATOR_AUTH.md").read_text()
            self.assertNotRegex(auth, r"gh auth token[^\n]*\|")
    
    def test_native_delivery_is_independent_of_build_worker_lifetime(self) -> None:
            paths = (
                DOCS / "LINUX_EXECUTION.md",
                DOCS / "COORDINATOR_AUTH.md",
                SKILLS / "atrinik-issue-delivery/references/preparation.md",
                SKILLS / "atrinik-multi-repo-workspace/SKILL.md",
                SKILLS / "atrinik-project-delivery/SKILL.md",
                SKILLS / "atrinik-project-delivery/references/coordinator.md",
            )
            for path in paths:
                text = " ".join(path.read_text(encoding="utf-8").split())
                with self.subTest(path=path):
                    self.assertIn("native", text.lower())
                    self.assertIn("worktree", text)
                    self.assertIn("container", text)
                    self.assertNotIn("A session is one agent-owned container", text)
            preparation = read_guidance_contract(
                SKILLS / "atrinik-issue-delivery/SKILL.md"
            )
            for gate in ("clean worktree", "ledger CAS and leases", "foreign or uncertain dirty work",
                         "umask 077", "standard private store", "selectors unset throughout"):
                self.assertIn(gate, " ".join(preparation.split()))
            execution = (DOCS / "LINUX_EXECUTION.md").read_text(encoding="utf-8")
            for invariant in ("same-absolute-path", "--pull never", "--expected-plan",
                              "--git-common-dir", "atrinik-resource-leases", "--cap-drop ALL",
                              "unchanged path and inode", "No mandatory host compiler", "cache keys",
                              "Distinct concurrent owners", "not a drop-in credential-free worker",
                              "no dirty-work adoption or ledger rewriting"):
                self.assertIn(invariant, execution)
            # The concrete worker arguments expose neither coordinator credentials
            # nor a Docker/display/GPU socket. Historical bound deliveries retain
            # their separate authentication and compatibility gates.
            arguments = execution.split("BUILD_ARGS=(", 1)[1].split("\n# Create, inspect", 1)[0]
            for forbidden in (".config/gh", ".codex", "docker.sock", "--privileged", "--gpus"):
                self.assertNotIn(forbidden, arguments)
            self.assertNotIn("mode=000", arguments)
            self.assertIn("/tmp:rw,exec,nosuid,nodev,mode=1777", arguments)
            self.assertIn("target=$REVIEW_ROOT,readonly", arguments)
            self.assertIn("never substitutes", " ".join(execution.split()))
            for required in ("$NATIVE_PRIMARY", "$NATIVE_WORKTREE", "$COMMON_GIT", "$BUILD_LEASES", "$REVIEW_ROOT"):
                self.assertIn(required, arguments)
    
    def test_issue_delivery_provisioning_examples_match_manifest(self) -> None:
            reference = (
                SKILLS
                / "atrinik-issue-delivery/references/delivery-ledger.md"
            ).read_text(encoding="utf-8")
            examples = [
                json.loads(match)
                for match in re.findall(r"```json\n(.*?)\n```", reference, re.DOTALL)
            ]
            pr_ledger = next(
                example
                for example in examples
                if isinstance(example, dict) and example.get("entry_mode") == "pr"
            )
            primitive = next(
                artifact["primitive_request"]
                for artifact in pr_ledger["artifacts"]
                if artifact.get("primitive_request") is not None
            )
            owner = primitive["repository"]["owner"]
            repository = primitive["repository"]["name"]
            self.assertEqual(
                primitive["repository"],
                {"owner": owner, "name": repository, "node_id": "R_repo"},
            )
            self.assertTrue(
                all(
                    target["repository"]["owner"] == owner
                    and target["repository"]["name"] == repository
                    for target in pr_ledger["targets"]
                )
            )
    
            issue_ledger = next(
                example
                for example in examples
                if isinstance(example, dict) and example.get("entry_mode") == "issue"
            )
            issue_worktree = next(
                artifact
                for artifact in issue_ledger["artifacts"]
                if artifact["kind"] == "worktree"
            )
            self.assertIsNone(issue_worktree["immutable"]["path"])
            self.assertIsNone(issue_worktree["producer_resource_slot"])
            issue_request = issue_worktree["primitive_request"]
            self.assertEqual(issue_request["component"], "atrinik")
            self.assertEqual(issue_request["physical_checkout"], "atrinik")
            self.assertEqual(
                issue_request["repository"],
                {"owner": "atrinik", "name": "atrinik", "node_id": "R_repo"},
            )
    
            scope = next(example[0] for example in examples if isinstance(example, list))
            self.assertEqual(
                scope["immutable"]["repository"],
                {"owner": "atrinik", "name": "client", "node_id": "R_repo"},
            )
    
    def test_removed_stale_routes_do_not_return(self) -> None:
            paths = sorted((SKILLS / "").glob("*/SKILL.md"))
            corpus = "\n".join(path.read_text(encoding="utf-8") for path in paths)
            for stale in {
                "mixed-component profile",
                "more than one standalone repository",
                "Today this seed repository",
                "scenario create NAME --state",
            }:
                with self.subTest(stale=stale):
                    self.assertNotIn(stale, corpus)
    
    def test_ssh_signing_guidance_is_optional_and_secret_safe(self) -> None:
            skill = (
                SKILLS / "atrinik-github-governance/SKILL.md"
            ).read_text(encoding="utf-8")
            reference = (
                SKILLS
                / "atrinik-github-governance/references/ssh-signing.md"
            ).read_text(encoding="utf-8")
            corpus = "\n".join((skill, reference))
            normalized = " ".join(corpus.split())
    
            for marker in {
                "SSH signing is optional",
                "Git 2.34",
                "Ed25519",
                "ssh-agent",
                "gpg.format ssh",
                "user.signingkey",
                "commit.gpgsign true",
                "gpgsig",
                "**Verified**",
                "Signed-off-by",
                "build workers receive no signing agent or credentials",
                "public key",
                "private signing key",
                "verified author email",
                "references/ssh-signing.md",
            }:
                with self.subTest(marker=marker):
                    self.assertIn(marker, normalized)
    
            self.assertNotRegex(
                corpus, r"-----BEGIN [^-]*PRIVATE KEY-----"
            )
            self.assertNotRegex(
                corpus,
                r"(?im)^\s*(?:all|every|each)\s+commits?\s+must\s+be\s+signed\b",
            )
            self.assertNotRegex(
                corpus,
                r"(?i)\b(?:signed commits|commit signing|commit signatures)\s+"
                r"(?:is|are)\s+(?:required|mandatory)\b",
            )
            self.assertNotRegex(
                corpus,
                r"(?i)\b(?:repository|project|organization)\s+"
                r"(?:requires|enforces|mandates)\s+"
                r"(?:signed commits|commit signing)\b",
            )
    
    def test_pull_request_publication_contract_is_synchronized(self) -> None:
            governance_skill = (
                SKILLS / "atrinik-github-governance/SKILL.md"
            )
            workspace_skill = (
                SKILLS / "atrinik-multi-repo-workspace/SKILL.md"
            )
            issue_delivery_skill = (
                SKILLS / "atrinik-issue-delivery/SKILL.md"
            )
            # The PR-body grammar is owned by CONTRIBUTING and GitHub governance.
            # Entry guides route to that authority instead of copying it.
            governed = [governance_skill]
            markers = {
                "type(optional-scope): concise description",
                "reviewer explicitly requests a breaking change",
                "GitHub-Flavored Markdown",
                "actual line breaks",
                "literal `\\n` separators",
                "multi-section",
            }
            substantive_markers = {
                "PR bodies must be substantive",
                "`Summary`",
                "`Implementation / behavior`",
                "`Validation`",
                "`Limitations / follow-up`",
                "issue-closing line alone is insufficient",
                "preserve contributor-authored text",
                "byte-for-byte",
                "delivery-owned section",
            }
            for path in governed:
                guidance = " ".join(path.read_text(encoding="utf-8").split())
                for marker in markers:
                    with self.subTest(path=path.relative_to(ROOT), marker=marker):
                        self.assertIn(marker, guidance)
                for marker in substantive_markers:
                    with self.subTest(
                        path=path.relative_to(ROOT), marker=marker
                    ):
                        self.assertIn(marker, guidance)
                with self.subTest(path=path.relative_to(ROOT), marker="no automatic !"):
                    self.assertNotIn(
                        "type(optional-scope)!: concise description", guidance
                    )
                with self.subTest(path=path.relative_to(ROOT), marker="body input"):
                    self.assertRegex(
                        guidance,
                        r"multi-section bod(?:y|ies)[^.]{0,200}file"
                        r"[^.]{0,200}(?:standard input|stdin)",
                    )
                with self.subTest(path=path.relative_to(ROOT), marker="remote render"):
                    self.assertRegex(
                        guidance,
                        r"[Aa]fter (?:create/edit|creating or editing a pull request)"
                        r"[^.]{0,160}(?:inspect|verify)[^.]{0,80}(?:remote|GitHub)",
                    )
    
            for path in [governance_skill]:
                guidance = " ".join(path.read_text(encoding="utf-8").split())
                for marker in {
                    "headings",
                    "lists",
                    "inline code",
                    "issue-closing references",
                    "validation sections",
                    "bodyHTML",
                    "raw body",
                }:
                    with self.subTest(path=path.relative_to(ROOT), marker=marker):
                        self.assertIn(marker, guidance)
    
            for path in [workspace_skill, issue_delivery_skill]:
                with self.subTest(path=path.relative_to(ROOT), route="governance"):
                    self.assertIn("atrinik-github-governance", path.read_text(encoding="utf-8"))
    
            _, governance_description = skill_frontmatter(governance_skill)
            self.assertIn("Publish Atrinik PRs", governance_description)
            governance_interface = (
                governance_skill.parent / "agents/openai.yaml"
            ).read_text(encoding="utf-8")
            self.assertIn("Publish PRs", governance_interface)
            self.assertIn("$atrinik-github-governance", governance_interface)
    
            unrelated = [
                path
                for path in (SKILLS / "").glob("*/SKILL.md")
                if path not in governed
            ]
            for path in unrelated:
                with self.subTest(path=path.relative_to(ROOT)):
                    guidance = " ".join(path.read_text(encoding="utf-8").split())
                    self.assertFalse(
                        all(marker in guidance for marker in markers),
                        "unrelated skill duplicates the complete PR publication contract",
                    )
    
    def test_issue_delivery_routes_new_and_retained_work_to_canonical_contracts(self) -> None:
            skill = SKILLS / "atrinik-issue-delivery"
            entry = (skill / "SKILL.md").read_text(encoding="utf-8")
            source = (DOCS / "SOURCE_DELIVERY.md").read_text(encoding="utf-8")
            preparation = (skill / "references/preparation.md").read_text(encoding="utf-8")
            ledger = (skill / "references/delivery-ledger.md").read_text(encoding="utf-8")
    
            for route in {
                "../../references/atrinik-workspace/docs/SOURCE_DELIVERY.md",
                "references/preparation.md",
                "references/delivery-ledger.md",
                "references/deep-review-checklist.md",
                "references/helper-lifecycle-review.md",
            }:
                self.assertIn(route, LINK.findall(entry))
            for invariant in {
                "it is not a delivery ledger",
                "--allow-dirty",
                "fixture tests cannot authorize live resources",
                "Missing acceptance is not a pass",
                "--expect",
            }:
                self.assertIn(invariant, source)
            for invariant in {
                "exact existing bound delivery",
                "bare `owner/repository#number` is ambiguous",
                "PR mode",
                "Before any delivery-owned mutation",
                "revalidate-current-targets-cas",
            }:
                self.assertIn(invariant, preparation)
            for invariant in {
                "authoritative schema-v1 sidecar",
                "generation/digest",
                "contributor-owned",
                "Treat any nonzero\nstatus as a stop, not permission to repair files manually",
            }:
                self.assertIn(invariant, ledger)
    
    

if __name__ == "__main__":
    unittest.main()
