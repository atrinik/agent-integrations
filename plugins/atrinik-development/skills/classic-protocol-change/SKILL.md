---
name: classic-protocol-change
description: Change Classic Atrinik command identities or packet contracts with coordinated schema, generator, producer, consumer, compatibility, and malformed-input validation. Use for Classic wire changes, not the replacement stack's protocol.
---

# Classic protocol changes

A wire change spans more than its declaration. Start with the exact producer,
receiver, and connection state that use the bytes. Follow the current Classic
root and `protocol/` guides, plus the guides of affected client, server, or library
code. Use one owned Classic monorepo worktree and a full isolated profile derived
from `classic`, as described in
[classic-native-change](../classic-native-change/SKILL.md).

Prefer a connected `atrinik` MCP for bounded discovery with an explicit Classic
profile and component. Read resource results, check their source commit against
the checkout, and narrow or paginate incomplete results. Local changes require
local inspection. A search snapshot never supersedes current repository rules
or supplies authority to run, write, or publish.

## Specify the transition

`protocol/schema/game-commands.json` owns shared command names and numeric IDs.
Some payload layouts live in endpoint implementations instead. Locate all uses
before deciding which files must change. Do not assign an endpoint-local ID or
copy generated constants into a consumer.

Describe the before/after contract sufficiently to construct and reject packets:

- Frame boundaries, header and payload lengths, field order, widths, signedness,
  byte order, maximum sizes, and representation of empty or absent values.
- Allowed connection states, command ordering, duplicate handling, and the point
  at which a complete packet may update application state.
- Revision negotiation and the behavior of an incompatible or unknown peer.
  Include reconnect: a fresh connection must not inherit obsolete decoder state.
- Errors for truncation, oversized lengths, invalid values, and unknown commands.
  Bound allocations and work before accepting untrusted length/count fields.

Preserve established IDs unless the task explicitly includes their breaking
transition. Choose one coordinated migration for all selected consumers; explain
the compatibility boundary and retire obsolete paths when the migration is done.
Keep rejected or partial packets from publishing half-applied state.

## Update sources and consumers together

Edit the schema for identity changes, or the owning packet implementation for
payload changes. Follow generated output back to its input. From the Classic
root, regenerate schema bindings when required:

```sh
python3 protocol/tools/generate.py
```

Review the resulting C and Python binding changes, then update every affected
encoder, decoder, test fixture, and dependency lock. Shared parsing or transport
logic belongs in `libatrinik/` when it is genuinely shared. Keep both endpoint
implementations in the same coordinated change; do not validate one endpoint
against a released sibling while the other uses the worktree.

If the change touches packaging or dependency resolution, verify sibling-source
selection and the standalone/embedded fallback. Follow the repository's unified
version and same-minor package compatibility rules; generated package versions
must agree with their owning release.

## Validate the contract, then its use

Create tests that distinguish the changed behavior. Exercise exact framing and
field bytes, zero and maximum boundaries, truncated fields, excessive counts,
wrong order, unknown commands, malformed values, and incompatible versions where
the affected contract admits them. Check encode/decode round trips and reconnect
state reset. Include a receiver-side test that failed parsing leaves state intact.

From the Classic root:

```sh
python3 protocol/tools/generate.py --check
python3 -m unittest discover -s protocol/tests -p 'test_*.py'
cmake -S protocol -B protocol/build -DCMAKE_BUILD_TYPE=Release
cmake --build protocol/build --parallel
ctest --test-dir protocol/build --output-on-failure
```

Run affected native suites from the wrapper root with the same resolved profile.
The usual shared-contract closure is:

```sh
./atrinik build libatrinik --profile PROFILE --test
./atrinik build server --profile PROFILE --test
./atrinik build client --profile PROFILE --test
```

Use current build-plan fencing and worker resource rules. Add module-specific
coverage/sanitizer and package checks when required. A successful generator check
only proves the generated files match their inputs; it cannot prove a payload
decoder or producer is correct.

If the contract changes live connection or gameplay behavior, use
[classic-runtime](../classic-runtime/SKILL.md) and observe the actual transition
on the coordinated client/server pair. Record connection/reconnect results and
any compatibility limitation without publishing credentials or packet secrets.

Finish the root-mandated checks:

```sh
python3 tools/verify_import_history.py
git diff --check
```

The handoff should identify the wire change, affected participants, revision
decision, tests and actual observations, plus any untested case. Skill use does
not authorize deployment, publication, or changes to shared runtime state.
