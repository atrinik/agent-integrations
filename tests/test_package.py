from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


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
CLASSIC_SKILLS = {
    "classic-native-change",
    "classic-protocol-change",
    "classic-runtime",
}
IMPORTED_SKILLS = EXPECTED_SKILLS - CLASSIC_SKILLS
MAX_IMPORTED_CATALOG_BYTES = 2_250
MAX_IMPORTED_SKILL_BYTES = 62_500
LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")
LOCAL_UPDATE_PATHS = {
    "plugins/atrinik-development/skills/atrinik-linux-gpu-qualification/references/linux-vulkan.md",
    "plugins/atrinik-development/skills/atrinik-multi-repo-workspace/SKILL.md",
}
CURRENT_UPDATE_PATHS = {"docs/LINUX_EXECUTION.md", "docs/WINDOWS_GPU_PREFLIGHT.md"}
PROVENANCE_BASELINE = "38a3f01939c67e5172e4a7eedd8f6330e9339bbd"
PROVENANCE_PATH = "plugins/atrinik-development/provenance.json"
LINK_TRANSFORMATION = "Retained package-relative links to the five packaged resources; replaced links outside the package with immutable source-revision URLs."
UNCHANGED_TRANSFORMATION = "Copied source bytes unchanged; all existing resource links remain package-relative."


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def recorded_git_bytes(revision: str, path: str) -> bytes:
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1"}
    try:
        kind = subprocess.check_output(
            ["git", "cat-file", "-t", revision], cwd=ROOT, env=env, stderr=subprocess.PIPE,
        )
        if kind != b"commit\n":
            raise ValueError("Recorded revision is not a commit")
        data = subprocess.check_output(
            ["git", "cat-file", "blob", f"{revision}:{path}"],
            cwd=ROOT, env=env, stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as error:
        raise ValueError("Recorded Git commit or blob is unavailable") from error
    return data


def recorded_git_blob(revision: str, path: str) -> str:
    data = recorded_git_bytes(revision, path)
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def validate_current_updates(records: list[dict]) -> None:
    baseline = json.loads(recorded_git_bytes(PROVENANCE_BASELINE, PROVENANCE_PATH))
    anchors = baseline.get("current_file_updates")
    if not isinstance(anchors, list) or not anchors or records[:len(anchors)] != anchors:
        raise ValueError("Historical current update prefix differs from immutable provider baseline")
    chains = {path: [] for path in CURRENT_UPDATE_PATHS}
    seen = set()
    for record in records:
        if set(record) != {"repository", "revision", "source_path", "destination_path",
                           "source_blob", "destination_blob", "license", "transformations", "link_updates"}:
            raise ValueError("Unexpected current update fields")
        path = record["source_path"]
        if path not in chains or record["destination_path"] != "plugins/atrinik-development/references/atrinik-workspace/" + path:
            raise ValueError("Unexpected current update path")
        license_record = record["license"]
        if (set(license_record) != {"spdx", "path", "blob"}
                or license_record["spdx"] != "MIT" or license_record["path"] != "LICENSE"):
            raise ValueError("Unexpected current update license")
        for value in (record["revision"], record["source_blob"], record["destination_blob"], license_record["blob"]):
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
                raise ValueError("Nonimmutable current update identity")
        identity = (path, record["revision"])
        if identity in seen:
            raise ValueError("Duplicate current update")
        seen.add(identity)
        source = recorded_git_bytes(record["revision"], path)
        if recorded_git_blob(record["revision"], path) != record["source_blob"]:
            raise ValueError("Current source blob mismatch")
        license_bytes = recorded_git_bytes(record["revision"], "LICENSE")
        if (recorded_git_blob(record["revision"], "LICENSE") != license_record["blob"]
                or license_bytes != (PLUGIN / "LICENSE").read_bytes()):
            raise ValueError("Current source MIT license mismatch")
        text = source.decode("utf-8")
        expected_links = []
        # Only these out-of-package links are rewritten; packaged resource links stay relative.
        for old, target in (("../README.md#pinned-build-and-runtime-containers", "README.md#pinned-build-and-runtime-containers"),
                            ("NATIVE_LINUX_TOOLCHAIN.md", "docs/NATIVE_LINUX_TOOLCHAIN.md"),
                            ("../README.md", "README.md")):
            if f"]({old})" in text:
                new = f"https://github.com/atrinik/atrinik/blob/{record['revision']}/{target}"
                expected_links.append({"source_target": old, "destination_target": new})
                text = text.replace(f"]({old})", f"]({new})")
        expected_description = LINK_TRANSFORMATION if expected_links else UNCHANGED_TRANSFORMATION
        if record["link_updates"] != expected_links or record["transformations"] != [expected_description]:
            raise ValueError("Unsupported or missing current link transformations")
        destination = text.encode("utf-8")
        actual_blob = hashlib.sha1(b"blob " + str(len(destination)).encode() + b"\0" + destination).hexdigest()
        if actual_blob != record["destination_blob"]:
            raise ValueError("Reconstructed current destination blob mismatch")
        chains[path].append((record, destination))
    for path in CURRENT_UPDATE_PATHS:
        if not chains[path]:
            raise ValueError("Missing retained current update chain")
        record, destination = chains[path][-1]
        if (ROOT / record["destination_path"]).read_bytes() != destination:
            raise ValueError("Terminal current update does not match package")


def validate_provenance_sources(provenance: dict) -> None:
    wrapper = "https://github.com/atrinik/atrinik.git"
    classic = "https://github.com/atrinik/classic.git"
    external = {key: value for key, value in provenance.items() if key != "local_authored_updates"}
    if set(repository_values(external)) != {wrapper, classic}:
        raise ValueError("Unexpected external provenance repository")
    for category in ("imports", "current_file_updates"):
        records = provenance.get(category, [])
        if not records or any(record.get("repository") != wrapper
                              or set(repository_values(record)) != {wrapper} for record in records):
            raise ValueError("Unexpected wrapper provenance repository")
    validate_current_updates(provenance["current_file_updates"])
    originals = provenance.get("original_work", [])
    if not originals:
        raise ValueError("Missing original work observations")
    for original in originals:
        observations = original.get("public_interface_observations", [])
        if [record.get("repository") for record in observations] != [classic, wrapper]:
            raise ValueError("Unexpected original work observation repository")
        for record in observations:
            if set(repository_values(record)) != {record["repository"]}:
                raise ValueError("Unexpected nested observation repository")
    records = provenance.get("local_authored_updates", [])
    if len(records) != len(LOCAL_UPDATE_PATHS):
        raise ValueError("Missing or duplicate local update")
    seen = set()
    for record in records:
        path = record["destination_path"]
        if path not in LOCAL_UPDATE_PATHS or path in seen:
            raise ValueError("Unexpected or duplicate local path")
        seen.add(path)
        if (record.get("repository") != "https://github.com/atrinik/agent-integrations.git"
                or set(repository_values(record)) != {"https://github.com/atrinik/agent-integrations.git"}):
            raise ValueError("Unexpected local provenance repository")
        baseline, license_record = record["baseline"], record["license"]
        for value in (record["revision"], record["source_blob"], record["destination_blob"],
                      baseline["revision"], baseline["blob"], license_record["blob"]):
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
                raise ValueError("Nonimmutable Git identity")
        prefix = f"https://github.com/atrinik/agent-integrations/blob/{record['revision']}/"
        if (record["source_path"] != path or baseline["path"] != path
                or record["source_url"] != prefix + path
                or record["source_blob"] != record["destination_blob"]
                or record["destination_blob"] != git_blob(ROOT / path)):
            raise ValueError("Local source or destination mismatch")
        if (license_record["spdx"] != "MIT" or license_record["path"] != "LICENSE"
                or license_record["source_url"] != prefix + "LICENSE"
                or license_record["blob"] != git_blob(ROOT / "LICENSE")):
            raise ValueError("Local MIT license mismatch")
        for revision, source_path, expected in (
            (record["revision"], record["source_path"], record["source_blob"]),
            (baseline["revision"], baseline["path"], baseline["blob"]),
            (record["revision"], license_record["path"], license_record["blob"]),
        ):
            if recorded_git_blob(revision, source_path) != expected:
                raise ValueError("Recorded Git object does not match provenance")
        transformations = record["transformations"]
        if (not isinstance(transformations, list) or not transformations
                or any(not isinstance(value, str) or not value.strip() for value in transformations)):
            raise ValueError("Missing local transformations")


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


def repository_values(value: object) -> list[str]:
    if isinstance(value, dict):
        repositories = [
            nested
            for key, nested in value.items()
            if key == "repository" and isinstance(nested, str)
        ]
        for nested in value.values():
            repositories.extend(repository_values(nested))
        return repositories
    if isinstance(value, list):
        return [
            repository
            for nested in value
            for repository in repository_values(nested)
        ]
    return []


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
        self.assertEqual(plugin["version"], "1.0.1")
        self.assertEqual(
            plugin["repository"],
            "https://github.com/atrinik/agent-integrations",
        )
        self.assertEqual(plugin["homepage"], plugin["repository"])
        self.assertEqual(
            plugin["extensions"]["com.openai"]["interface"]["websiteURL"],
            plugin["repository"],
        )
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

    def test_imported_skill_catalog_and_bodies_preserve_budgets(self) -> None:
        catalog = "".join(
            f"{name}\t{frontmatter(SKILLS / name / 'SKILL.md')['description']}\t"
            f".agents/skills/{name}/SKILL.md\n"
            for name in sorted(IMPORTED_SKILLS)
        )
        catalog_bytes = len(catalog.encode("utf-8"))
        skill_bytes = sum(
            len((SKILLS / name / "SKILL.md").read_bytes())
            for name in IMPORTED_SKILLS
        )
        self.assertLessEqual(
            catalog_bytes,
            MAX_IMPORTED_CATALOG_BYTES,
            f"imported skill catalog is {catalog_bytes} bytes",
        )
        self.assertLessEqual(
            skill_bytes,
            MAX_IMPORTED_SKILL_BYTES,
            f"imported SKILL.md bodies are {skill_bytes} bytes",
        )

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
        validate_provenance_sources(provenance)
        for item in provenance["original_work"]:
            self.assertIn("atrinik/agent-integrations", item["origin"])

    def test_local_provenance_rejects_invalid_sources(self) -> None:
        original = json.loads((PLUGIN / "provenance.json").read_text(encoding="utf-8"))
        mutations = {
            "wrong repository": lambda p: p["local_authored_updates"][0].update(repository="https://example.com/foreign.git"),
            "wrong category": lambda p: p["current_file_updates"].append(p["local_authored_updates"].pop()),
            "duplicate path": lambda p: p["local_authored_updates"].__setitem__(1, copy.deepcopy(p["local_authored_updates"][0])),
            "outside package": lambda p: p["local_authored_updates"][0].update(destination_path="../foreign.md"),
            "short revision": lambda p: p["local_authored_updates"][0].update(revision="f723d04"),
            "wrong URL": lambda p: p["local_authored_updates"][0].update(source_url="https://example.com/source"),
            "wrong baseline path": lambda p: p["local_authored_updates"][0]["baseline"].update(path="LICENSE"),
            "wrong blob": lambda p: p["local_authored_updates"][0].update(source_blob="0" * 40, destination_blob="0" * 40),
            "wrong license": lambda p: p["local_authored_updates"][0]["license"].update(spdx="GPL-2.0-or-later"),
            "wrong license blob": lambda p: p["local_authored_updates"][0]["license"].update(blob="0" * 40),
            "missing transformations": lambda p: p["local_authored_updates"][0].update(transformations=[]),
        }
        for name, mutate in mutations.items():
            with self.subTest(case=name):
                candidate = copy.deepcopy(original)
                mutate(candidate)
                with self.assertRaises(ValueError):
                    validate_provenance_sources(candidate)

    def test_provenance_rejects_unverified_git_objects_and_record_origins(self) -> None:
        original = json.loads((PLUGIN / "provenance.json").read_text(encoding="utf-8"))

        def change_source_revision(provenance: dict, revision: str) -> None:
            record = provenance["local_authored_updates"][0]
            old = record["revision"]
            record["revision"] = revision
            record["source_url"] = record["source_url"].replace(old, revision)
            record["license"]["source_url"] = record["license"]["source_url"].replace(old, revision)

        mutations = {
            "nonexistent source commit": lambda p: change_source_revision(p, "0" * 40),
            "source commit with different blob": lambda p: change_source_revision(p, p["local_authored_updates"][0]["baseline"]["revision"]),
            "nonexistent baseline commit": lambda p: p["local_authored_updates"][0]["baseline"].update(revision="0" * 40),
            "wrong baseline blob": lambda p: p["local_authored_updates"][0]["baseline"].update(blob="0" * 40),
            "deleted import repository": lambda p: p["imports"][0].pop("repository"),
            "deleted current repository": lambda p: p["current_file_updates"][0].pop("repository"),
            "deleted local repository": lambda p: p["local_authored_updates"][0].pop("repository"),
            "import relabeled Classic": lambda p: p["imports"][0].update(repository="https://github.com/atrinik/classic.git"),
            "current relabeled Classic": lambda p: p["current_file_updates"][0].update(repository="https://github.com/atrinik/classic.git"),
            "Classic observation relabeled wrapper": lambda p: p["original_work"][0]["public_interface_observations"][0].update(repository="https://github.com/atrinik/atrinik.git"),
            "wrapper observation relabeled Classic": lambda p: p["original_work"][0]["public_interface_observations"][1].update(repository="https://github.com/atrinik/classic.git"),
            "deleted observation repository": lambda p: p["original_work"][0]["public_interface_observations"][0].pop("repository"),
        }
        for name, mutate in mutations.items():
            with self.subTest(case=name):
                candidate = copy.deepcopy(original)
                mutate(candidate)
                with self.assertRaises(ValueError):
                    validate_provenance_sources(candidate)

    def test_current_provenance_rejects_corrupt_objects_links_and_chains(self) -> None:
        original = json.loads((PLUGIN / "provenance.json").read_text())
        mutations = {
            "missing source commit": lambda p: p["current_file_updates"][0].update(revision="0" * 40),
            "short source commit": lambda p: p["current_file_updates"][0].update(revision="a9661a2"),
            "wrong source blob": lambda p: p["current_file_updates"][0].update(source_blob="0" * 40),
            "wrong source path": lambda p: p["current_file_updates"][0].update(source_path="docs/COORDINATOR_AUTH.md"),
            "outside destination": lambda p: p["current_file_updates"][0].update(destination_path="../foreign.md"),
            "wrong destination blob": lambda p: p["current_file_updates"][0].update(destination_blob="0" * 40),
            "wrong SPDX": lambda p: p["current_file_updates"][0]["license"].update(spdx="GPL-2.0-or-later"),
            "wrong license blob": lambda p: p["current_file_updates"][0]["license"].update(blob="0" * 40),
            "wrong license path": lambda p: p["current_file_updates"][0]["license"].update(path="README.md"),
            "wrong source link": lambda p: p["current_file_updates"][0]["link_updates"][0].update(source_target="../foreign.md"),
            "wrong destination link": lambda p: p["current_file_updates"][0]["link_updates"][0].update(destination_target="https://example.com/foreign"),
            "missing link edit": lambda p: p["current_file_updates"][0]["link_updates"].pop(),
            "wrong transformation": lambda p: p["current_file_updates"][0].update(transformations=["Unrecorded byte changes"]),
            "missing old Linux chain entry": lambda p: p["current_file_updates"].pop(0),
            "missing terminal Linux chain entry": lambda p: p["current_file_updates"].pop(),
            "missing Windows entry": lambda p: p["current_file_updates"].pop(1),
            "duplicate update": lambda p: p["current_file_updates"].append(copy.deepcopy(p["current_file_updates"][0])),
            "reversed chain": lambda p: p["current_file_updates"].reverse(),
        }
        for name, mutate in mutations.items():
            with self.subTest(case=name):
                candidate = copy.deepcopy(original)
                mutate(candidate)
                with self.assertRaises(ValueError):
                    validate_provenance_sources(candidate)

    def test_current_provenance_retains_actual_immutable_baseline_prefix(self) -> None:
        original = json.loads((PLUGIN / "provenance.json").read_text())
        baseline = json.loads(recorded_git_bytes(PROVENANCE_BASELINE, PROVENANCE_PATH))
        anchors = baseline["current_file_updates"]
        self.assertEqual(original["current_file_updates"][:len(anchors)], anchors)
        # A different trusted Root snapshot can reproduce the exact current Windows bytes.
        alternative = copy.deepcopy(original)
        record = alternative["current_file_updates"][1]
        revision = original["current_file_updates"][-1]["revision"]
        record["revision"] = revision
        record["source_blob"] = recorded_git_blob(revision, record["source_path"])
        record["destination_blob"] = record["source_blob"]
        record["license"]["blob"] = recorded_git_blob(revision, "LICENSE")
        self.assertEqual(recorded_git_bytes(revision, record["source_path"]),
                         (ROOT / record["destination_path"]).read_bytes())
        with self.assertRaises(ValueError):
            validate_provenance_sources(alternative)
        for bad in ("0" * 40, recorded_git_blob(PROVENANCE_BASELINE, PROVENANCE_PATH)):
            with self.subTest(anchor=bad), patch(__name__ + ".PROVENANCE_BASELINE", bad):
                with self.assertRaises(ValueError):
                    validate_provenance_sources(original)

    def test_recorded_git_blob_requires_commit_and_existing_blob(self) -> None:
        record = json.loads((PLUGIN / "provenance.json").read_text(encoding="utf-8"))["local_authored_updates"][0]
        self.assertEqual(recorded_git_blob(record["revision"], record["source_path"]), record["source_blob"])
        self.assertEqual(recorded_git_blob(record["revision"], "LICENSE"), record["license"]["blob"])
        for revision, path in (("0" * 40, "LICENSE"), (record["source_blob"], "LICENSE"),
                               (record["revision"], "missing-provenance-source")):
            with self.subTest(revision=revision, path=path), self.assertRaises(ValueError):
                recorded_git_blob(revision, path)

    def test_provenance_hydration_restores_source_after_squash(self) -> None:
        workflow = (ROOT / ".github/workflows/validate.yml").read_text()
        block = workflow.split("      - name: Fetch immutable local provenance objects\n", 1)[1]
        block = block.split("        run: |\n", 1)[1].split("\n      - name:", 1)[0]
        script = "\n".join(line[10:] for line in block.splitlines()) + "\n"
        canonical = "repository = 'https://github.com/atrinik/agent-integrations.git'"
        root_canonical = "root_repository = 'https://github.com/atrinik/atrinik.git'"
        self.assertIn(canonical, script)
        self.assertIn(root_canonical, script)
        provenance = json.loads((PLUGIN / "provenance.json").read_text())
        source = provenance["local_authored_updates"][0]["revision"]
        baseline = provenance["local_authored_updates"][0]["baseline"]["revision"]
        env = {**os.environ, "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
               "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
               "GIT_TERMINAL_PROMPT": "0", "GIT_NO_LAZY_FETCH": "1"}
        env.pop("GIT_ALTERNATE_OBJECT_DIRECTORIES", None)

        def git(directory: Path, *args: str) -> str:
            return subprocess.check_output(["git", *args], cwd=directory, env=env,
                                           stderr=subprocess.PIPE, text=True).strip()

        with tempfile.TemporaryDirectory(prefix="provenance-squash-") as temporary:
            origin, checkout = Path(temporary) / "origin", Path(temporary) / "checkout"
            root_origin = Path(temporary) / "root-origin"
            root_origin.mkdir()
            git(root_origin, "init")
            root_revisions = {record["revision"] for record in provenance["current_file_updates"]}
            provider_objects = Path(git(ROOT, "rev-parse", "--git-path", "objects"))
            if not provider_objects.is_absolute():
                provider_objects = ROOT / provider_objects
            object_sources = [str(provider_objects), *filter(None, os.environ.get("GIT_ALTERNATE_OBJECT_DIRECTORIES", "").split(os.pathsep))]
            (root_origin / ".git/objects/info/alternates").write_text("\n".join(object_sources) + "\n")
            origin.mkdir()
            git(origin, "init")
            git(origin, "fetch", "--update-shallow", "--no-tags", str(ROOT), "HEAD")
            tree = git(origin, "rev-parse", "FETCH_HEAD^{tree}")
            squash = git(origin, "commit-tree", tree, "-p", baseline, "-m", "Synthetic squash")
            git(origin, "update-ref", "refs/heads/main", squash)
            git(origin, "clone", "--no-local", "--depth=2", "--single-branch", "--branch", "main", str(origin), str(checkout))
            anchor_blob = git(ROOT, "rev-parse", f"{PROVENANCE_BASELINE}:{PROVENANCE_PATH}")
            missing_anchor = subprocess.run(["git", "cat-file", "-e", PROVENANCE_BASELINE],
                                            cwd=checkout, env=env, capture_output=True)
            self.assertNotEqual(missing_anchor.returncode, 0)
            missing = subprocess.run(["git", "cat-file", "-e", source], cwd=checkout,
                                     env=env, capture_output=True)
            self.assertNotEqual(missing.returncode, 0)
            for revision in root_revisions:
                missing = subprocess.run(["git", "cat-file", "-e", revision], cwd=checkout,
                                         env=env, capture_output=True)
                self.assertNotEqual(missing.returncode, 0)
            # Use only a controlled local source in this fixture; CI keeps the fixed public URL.
            local_script = script.replace(canonical, f"repository = {str(ROOT)!r}")
            local_script = local_script.replace(root_canonical, f"root_repository = {str(root_origin)!r}")
            # Records retain the public identity while transport is replaced for this offline fixture.
            local_script = local_script.replace("record.get('repository') != repository",
                                                "record.get('repository') != 'https://github.com/atrinik/agent-integrations.git'")
            local_script = local_script.replace("update.get('repository') != root_repository",
                                                "update.get('repository') != 'https://github.com/atrinik/atrinik.git'")
            shallow_file = checkout / ".git/shallow"
            self.assertTrue(shallow_file.is_file())
            shallow_before = shallow_file.read_bytes()
            refs_before = git(checkout, "for-each-ref", "--format=%(refname) %(objectname)")
            history_before = git(checkout, "rev-list", "--all")
            subprocess.run([sys.executable, "-B", "-c", local_script], cwd=checkout,
                           env=env, check=True, capture_output=True)
            self.assertEqual(shallow_file.read_bytes(), shallow_before)
            self.assertEqual(git(checkout, "for-each-ref", "--format=%(refname) %(objectname)"), refs_before)
            self.assertEqual(git(checkout, "rev-list", "--all"), history_before)
            self.assertEqual(git(checkout, "cat-file", "-t", source), "commit")
            self.assertEqual(git(checkout, "rev-parse", f"{PROVENANCE_BASELINE}:{PROVENANCE_PATH}"), anchor_blob)
            subprocess.run([sys.executable, "-B", "-m", "unittest",
                            "tests.test_package.PackageTests.test_installed_package_retains_license_and_provenance"],
                           cwd=checkout, env=env, check=True, capture_output=True)
            # Even an already-cached exact commit must be refused if its remote cannot serve it.
            empty_remote = Path(temporary) / "empty.git"
            git(origin, "init", "--bare", str(empty_remote))
            cached_bypass = subprocess.run(["git", "fetch", "--no-tags", "--no-write-fetch-head",
                                           str(empty_remote), baseline], cwd=checkout, env=env, capture_output=True)
            self.assertEqual(cached_bypass.returncode, 0)
            unavailable_remote_script = local_script.replace(f"repository = {str(ROOT)!r}",
                                                               f"repository = {str(empty_remote)!r}")
            refused_remote = subprocess.run([sys.executable, "-B", "-c", unavailable_remote_script],
                                             cwd=checkout, env=env, capture_output=True)
            self.assertNotEqual(refused_remote.returncode, 0)
            # An unavailable exact commit must fail hydration rather than silently using current files.
            record_path = checkout / "plugins/atrinik-development/provenance.json"
            invalid = json.loads(record_path.read_text())
            invalid["local_authored_updates"][0]["revision"] = "0" * 40
            record_path.write_text(json.dumps(invalid))
            refused = subprocess.run([sys.executable, "-B", "-c", local_script], cwd=checkout,
                                     env=env, capture_output=True)
            self.assertNotEqual(refused.returncode, 0)

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

            current.unlink()
            historical.unlink()
            with tempfile.TemporaryDirectory(prefix="unaccepted candidate ") as outside_dir:
                outside = Path(outside_dir) / "delivery_ledger.py"
                outside.write_text("candidate", encoding="utf-8")
                current.symlink_to(outside)
                rejected = subprocess.run(
                    ["sh", "-c", selection], cwd="/", env=env,
                    check=False, capture_output=True, text=True,
                )
                self.assertNotEqual(rejected.returncode, 0)
                self.assertNotIn(str(outside), rejected.stdout)

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
        provider_tests = {
            match.group(1)
            for path in (ROOT / "tests").glob("test_*.py")
            for match in re.finditer(
                r"(?m)^    def (test_[a-z0-9_]+)\(",
                path.read_text(encoding="utf-8"),
            )
        }
        for item in transfer["transfers"]:
            with self.subTest(source_test=item["source_test"]):
                self.assertIn(item["provider_test"], provider_tests)


if __name__ == "__main__":
    unittest.main()
