from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/atrinik-development"
SKILLS = PLUGIN / "skills"
EXPECTED_SKILLS = {
    "atrinik-c-change",
    "atrinik-content-change",
    "atrinik-github-governance",
    "atrinik-guidance-maintenance",
    "atrinik-issue-delivery",
    "atrinik-linux-gpu-qualification",
    "atrinik-multi-repo-workspace",
    "atrinik-program-delivery",
    "atrinik-project-delivery",
    "atrinik-protocol-change",
    "atrinik-server-runtime",
    "atrinik-test-scenario",
    "classic-native-change",
    "classic-protocol-change",
    "classic-runtime",
}
LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError(f"invalid frontmatter: {path}")
    values: dict[str, str] = {}
    for line in text.split("---\n", 2)[1].splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip()
    return values


class PackageTests(unittest.TestCase):
    def test_marketplace_and_plugin_manifests_are_consistent(self) -> None:
        marketplace = json.loads(
            (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        plugin = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
        codex = json.loads(
            (PLUGIN / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(marketplace["name"], "atrinik")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "atrinik-development")
        self.assertEqual(entry["source"], {
            "path": "./plugins/atrinik-development",
            "source": "local",
        })
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(plugin["name"], entry["name"])
        self.assertEqual(codex["name"], entry["name"])
        self.assertEqual(plugin["version"], codex["version"])
        self.assertEqual(codex["skills"], "./skills/")
        self.assertEqual(plugin["repository"], "https://github.com/atrinik/agent-skills")
        self.assertEqual(plugin["license"], "MIT")

    def test_all_fifteen_skills_have_complete_metadata(self) -> None:
        actual = {path.name for path in SKILLS.iterdir() if path.is_dir()}
        self.assertEqual(actual, EXPECTED_SKILLS)
        explicit_false = {
            "atrinik-issue-delivery",
            "atrinik-program-delivery",
        }
        explicit_true = {
            "classic-native-change",
            "classic-protocol-change",
            "classic-runtime",
        }
        for name in sorted(EXPECTED_SKILLS):
            skill = SKILLS / name
            with self.subTest(skill=name):
                metadata = frontmatter(skill / "SKILL.md")
                self.assertEqual(metadata["name"], name)
                self.assertTrue(metadata.get("description"))
                interface = (skill / "agents/openai.yaml").read_text(encoding="utf-8")
                self.assertIn("interface:", interface)
                policy = re.search(
                    r"(?m)^  allow_implicit_invocation: (true|false)$",
                    interface,
                )
                if name in explicit_false:
                    self.assertIsNotNone(policy)
                    self.assertEqual(policy.group(1), "false")
                elif name in explicit_true:
                    self.assertIsNotNone(policy)
                    self.assertEqual(policy.group(1), "true")
                else:
                    self.assertIsNone(policy)

    def test_canonical_package_has_no_private_runtime_payload(self) -> None:
        self.assertFalse((PLUGIN / "server").exists())
        self.assertFalse((PLUGIN / "config").exists())
        self.assertFalse((PLUGIN / "bundle-manifest.json").exists())
        self.assertFalse((PLUGIN / "skills/atrinik-issue-delivery/scripts/delivery_ledger.py").exists())
        self.assertEqual(
            {path.name for path in PLUGIN.iterdir()},
            {".codex-plugin", "LICENSE", "plugin.json", "provenance.json", "references", "skills"},
        )

    def test_installed_package_retains_license_and_provenance(self) -> None:
        notice = (PLUGIN / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", notice)
        self.assertIn("Copyright (c) 2026 Atrinik contributors", notice)
        provenance = json.loads((PLUGIN / "provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["schema_version"], 1)
        self.assertIsNone(provenance["policy"]["self_revision_pin"])
        imported = provenance["imports"][0]
        self.assertEqual(imported["repository"], "https://github.com/atrinik/atrinik.git")
        self.assertEqual(imported["revision"], "476cf9dad436ce7b5fb89113c46014fcca3b8f77")
        self.assertEqual(imported["license"]["spdx"], "MIT")
        self.assertEqual(len(imported["skills"]), 12)
        self.assertEqual(len(imported["resources"]), 5)
        self.assertEqual(len(provenance["original_work"]), 3)
        self.assertNotIn("agent-integrations", json.dumps(provenance))

    def test_local_links_resolve_within_package(self) -> None:
        paths = sorted(PLUGIN.rglob("*.md"))
        for path in paths:
            for raw_target in LINK.findall(path.read_text(encoding="utf-8")):
                target = raw_target.split("#", 1)[0]
                if not target or "://" in target:
                    continue
                with self.subTest(path=path.relative_to(ROOT), target=raw_target):
                    resolved = (path.parent / target).resolve()
                    self.assertTrue(resolved.is_relative_to(PLUGIN.resolve()))
                    self.assertTrue(resolved.is_file())

    def test_delivery_helper_selection_supports_both_accepted_locations(self) -> None:
        reference = (
            SKILLS / "atrinik-issue-delivery/references/delivery-ledger.md"
        ).read_text(encoding="utf-8")
        block = re.search(r"```sh\n(?P<body>.*?)\n```", reference, re.DOTALL)
        self.assertIsNotNone(block)
        body = block.group("body")
        selection = body[body.index("if ["):body.index("readonly DELIVERY_LEDGER_HELPER")]
        selection += "readonly DELIVERY_LEDGER_HELPER\nprintf '%s' \"$DELIVERY_LEDGER_HELPER\"\n"

        with tempfile.TemporaryDirectory(prefix="accepted wrapper ") as temporary:
            wrapper = Path(temporary)
            current = wrapper / "scripts/delivery_ledger.py"
            historical = wrapper / ".agents/skills/atrinik-issue-delivery/scripts/delivery_ledger.py"
            historical.parent.mkdir(parents=True)
            historical.write_text("historical", encoding="utf-8")
            env = {**os.environ, "DELIVERY_WRAPPER_ROOT": str(wrapper), "UNTRUSTED_HELPER": "/tmp/candidate.py"}
            with tempfile.TemporaryDirectory(prefix="unrelated cwd ") as cwd:
                result = subprocess.run(
                    ["sh", "-c", selection], cwd=cwd, env=env,
                    check=True, capture_output=True, text=True,
                )
            self.assertEqual(result.stdout, str(historical))

            current.parent.mkdir(parents=True)
            current.write_text("current", encoding="utf-8")
            result = subprocess.run(
                ["sh", "-c", selection], cwd="/", env=env,
                check=True, capture_output=True, text=True,
            )
            self.assertEqual(result.stdout, str(current))
            self.assertNotEqual(result.stdout, env["UNTRUSTED_HELPER"])

    def test_delivery_helper_guidance_fails_closed_on_candidate_paths(self) -> None:
        paths = [
            SKILLS / "atrinik-issue-delivery/references/delivery-ledger.md",
            SKILLS / "atrinik-issue-delivery/references/resource-observation-recovery.md",
            PLUGIN / "references/atrinik-workspace/docs/RUNTIME_HANDOFF.md",
        ]
        corpus = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertNotIn("python3 scripts/delivery_ledger.py", corpus)
        self.assertIn('python3 "$DELIVERY_LEDGER_HELPER"', corpus)
        self.assertIn("candidate repair branch", corpus)
        self.assertIn("current-working-directory path", corpus)
        self.assertIn("when the accepted wrapper path contains\nspaces", corpus)

    def test_transfer_manifest_covers_each_migrated_source_test(self) -> None:
        transfer = json.loads(
            (ROOT / "tests/transfer_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(transfer["source"]["revision"], "476cf9dad436ce7b5fb89113c46014fcca3b8f77")
        names = [item["source_test"] for item in transfer["transfers"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertGreaterEqual(len(names), 20)


if __name__ == "__main__":
    unittest.main()
