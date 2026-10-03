"""Exercise published command examples against small synthetic interface models.

These tests check command compatibility and state flow, not actual Atrinik builds
or model compliance with prose. Independent forward review covers agent decisions.
No fixture reads a checkout, spawns a process, or obtains real credentials.
"""

from pathlib import Path
import re
import shlex
import unittest


SKILLS = Path(__file__).resolve().parents[1] / "plugins/atrinik-development/skills"


def command_blocks(skill, profile="classic-fixture", name="player-fixture"):
    source = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    return [
        [shlex.split(line.replace("PROFILE", profile).replace("NAME", name))
         for line in block.splitlines() if line.strip()]
        for block in re.findall(r"```sh\n(.*?)```", source, flags=re.S)
    ]


class SyntheticWrapper:
    """Model only the public commands used by these examples; reject all others."""

    def __init__(self, authorized=True):
        self.authorized = authorized
        self.profiles = {"classic-fixture", "classic-second"}
        self.scenarios = {}
        self.inspected = set()
        self.topologies = {}
        self.builds = set()
        self.calls = []
        self.secret_reads = 0

    def run(self, command):
        self.calls.append(command)
        if not command or command[0] != "./atrinik":
            raise ValueError("not a wrapper command")
        args = command[1:]
        match args:
            case ["profile", "show", profile, "--json"]:
                self._profile(profile)
                return {"profile": profile}
            case ["topology", "show", profile]:
                self._profile(profile)
                return {"profile": profile}
            case ["build", component, "--profile", profile, "--test"]:
                self._profile(profile)
                if component not in {"libatrinik", "server", "client"}:
                    raise ValueError("unknown native component")
                self.builds.add((profile, component))
            case ["scenario", "create", name, "--profile", profile,
                  "--preset", "basic-player"]:
                self._profile(profile)
                self._authorized()
                if name in self.scenarios:
                    raise PermissionError("scenario name already belongs to a task")
                self.scenarios[name] = (profile, "scenario-" + name, "this-task")
            case ["scenario", "show", name, "--json"]:
                profile, state, owner = self.scenarios[name]
                return {"profile": profile, "state": state}
            case ["topology", "show", profile, "--state", state, "--json"]:
                self._profile(profile)
                self.inspected.add((profile, state))
            case ["up", "--name", name, "--profile", profile, "--state", state]:
                self._authorized()
                self._profile(profile)
                self._owned_scenario(name)
                if self.scenarios[name][:2] != (profile, state):
                    raise ValueError("profile or state drift")
                if (profile, state) not in self.inspected:
                    raise ValueError("topology must be inspected before startup")
                self.topologies[name] = "running"
            case ["ps", name, "--json"]:
                return {"status": self.topologies[name]}
            case ["logs", name, service, "--tail", count]:
                if self.topologies[name] != "running":
                    raise ValueError("service is not running")
                if service not in {"server", "client"} or not 0 < int(count) <= 200:
                    raise ValueError("unexpected service or unbounded log request")
                return {"message": "synthetic nonsecret service event"}
            case ["down", name]:
                self._authorized()
                self._owned_scenario(name)
                self.topologies[name] = "stopped"
            case ["scenario", "credentials", name]:
                self.secret_reads += 1
                raise PermissionError("credential output excluded from public examples")
            case _:
                raise ValueError("unsupported command in published example")

    def _profile(self, profile):
        if profile not in self.profiles:
            raise ValueError("profile is not selected")

    def _authorized(self):
        if not self.authorized:
            raise PermissionError("runtime authority denied")

    def _owned_scenario(self, name):
        if self.scenarios[name][2] != "this-task":
            raise PermissionError("scenario belongs to another task")


def execute(commands, endpoint):
    """Fail at the failing command; never turn a denial into a later success."""
    return [endpoint.run(command) for command in commands]


class SyntheticProtocol:
    def __init__(self, generated_current=True, decoder_pass=True):
        self.generated_current = generated_current
        self.decoder_pass = decoder_pass
        self.configured = False
        self.built = False
        self.checked = False
        self.calls = []

    def run(self, command):
        self.calls.append(command)
        match command:
            case ["python3", "protocol/tools/generate.py", "--check"]:
                if not self.generated_current:
                    raise RuntimeError("generated bindings differ")
                self.checked = True
            case ["python3", "-m", "unittest", "discover", "-s", "protocol/tests",
                  "-p", "test_*.py"]:
                if not self.decoder_pass:
                    raise RuntimeError("malformed packet regression")
            case ["cmake", "-S", "protocol", "-B", "protocol/build",
                  "-DCMAKE_BUILD_TYPE=Release"]:
                self.configured = True
            case ["cmake", "--build", "protocol/build", "--parallel"]:
                if not self.configured:
                    raise RuntimeError("configure missing")
                self.built = True
            case ["ctest", "--test-dir", "protocol/build", "--output-on-failure"]:
                if not self.built:
                    raise RuntimeError("build missing")
            case _:
                raise ValueError("unsupported protocol verification command")


class ClassicWorkflowTests(unittest.TestCase):
    def test_scenario_lifecycle_keeps_state_profile_and_ownership_consistent(self):
        wrapper = SyntheticWrapper()
        for block in command_blocks("classic-runtime"):
            execute(block, wrapper)
        self.assertEqual(wrapper.topologies, {"player-fixture": "stopped"})
        self.assertEqual(wrapper.scenarios["player-fixture"],
                         ("classic-fixture", "scenario-player-fixture", "this-task"))
        self.assertEqual(wrapper.secret_reads, 0)
        self.assertEqual(wrapper.calls[-1], ["./atrinik", "ps", "player-fixture", "--json"])

    def test_concurrent_examples_use_disjoint_names_and_states(self):
        wrapper = SyntheticWrapper()
        first = command_blocks("classic-runtime")
        second = command_blocks("classic-runtime", "classic-second", "second-fixture")
        for block in first[:-1] + second[:-1]:
            execute(block, wrapper)
        execute(first[-1], wrapper)
        self.assertEqual(wrapper.topologies["second-fixture"], "running")
        execute(second[-1], wrapper)
        self.assertEqual(set(wrapper.topologies.values()), {"stopped"})

    def test_foreign_scenario_is_not_replaced_or_started(self):
        wrapper = SyntheticWrapper()
        wrapper.scenarios["player-fixture"] = ("classic-fixture", "scenario-player-fixture", "other-task")
        with self.assertRaises(PermissionError):
            execute(command_blocks("classic-runtime")[0], wrapper)
        self.assertEqual(wrapper.scenarios["player-fixture"][2], "other-task")
        self.assertFalse(wrapper.topologies)

    def test_denial_at_start_has_no_following_process_or_log_claim(self):
        wrapper = SyntheticWrapper()
        blocks = command_blocks("classic-runtime")
        execute(blocks[0], wrapper)
        wrapper.authorized = False
        with self.assertRaises(PermissionError):
            execute(blocks[1], wrapper)
        self.assertEqual(wrapper.calls[-1][1], "up")
        self.assertFalse(wrapper.topologies)
        self.assertEqual(wrapper.secret_reads, 0)

    def test_behavior_failure_can_still_stop_owned_runtime(self):
        wrapper = SyntheticWrapper()
        blocks = command_blocks("classic-runtime")
        execute(blocks[0] + blocks[1], wrapper)
        try:
            raise AssertionError("synthetic feature observation did not match")
        except AssertionError:
            execute(blocks[2], wrapper)
        self.assertEqual(wrapper.topologies["player-fixture"], "stopped")

    def test_shared_native_api_examples_cover_both_consumers(self):
        for skill in ("classic-native-change", "classic-protocol-change"):
            with self.subTest(skill=skill):
                wrapper = SyntheticWrapper()
                builds = [cmd for block in command_blocks(skill) for cmd in block
                          if cmd[:2] == ["./atrinik", "build"]]
                execute(builds, wrapper)
                self.assertEqual(wrapper.builds, {
                    ("classic-fixture", "libatrinik"),
                    ("classic-fixture", "server"),
                    ("classic-fixture", "client"),
                })

    def protocol_checks(self):
        return next(block for block in command_blocks("classic-protocol-change")
                    if block[0] == ["python3", "protocol/tools/generate.py", "--check"])

    def test_protocol_check_builds_before_ctest_without_regenerating(self):
        protocol = SyntheticProtocol()
        execute(self.protocol_checks(), protocol)
        self.assertTrue(protocol.checked)
        self.assertTrue(protocol.configured)
        self.assertTrue(protocol.built)
        self.assertEqual(protocol.calls[-1][0], "ctest")

    def test_stale_generated_output_stops_verification(self):
        protocol = SyntheticProtocol(generated_current=False)
        with self.assertRaises(RuntimeError):
            execute(self.protocol_checks(), protocol)
        self.assertFalse(protocol.built)
        self.assertFalse(protocol.generated_current)

    def test_matching_generated_output_does_not_hide_decoder_failure(self):
        protocol = SyntheticProtocol(decoder_pass=False)
        with self.assertRaises(RuntimeError):
            execute(self.protocol_checks(), protocol)
        self.assertTrue(protocol.checked)
        self.assertFalse(protocol.built)


if __name__ == "__main__":
    unittest.main()
