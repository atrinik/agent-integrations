---
name: classic-runtime
description: Run and verify an isolated Classic Atrinik client/server scenario through the workspace wrapper, including prerequisites, behavioral proof, logs, and cleanup. Use for Classic gameplay, rendering, persistence, or connection checks that need a running system.
---

# Classic runtime verification

Choose a concrete observation before starting: for example, the player enters
the expected map, a second connection receives the changed packet correctly, or
a saved value survives a controlled restart. Name the action and expected result
so process health cannot be mistaken for feature proof.

## Resolve prerequisites and ownership

Read current wrapper and Classic component guidance. Use the wrapper's profile,
worktree, state, scenario, and topology interfaces; it owns process supervision,
port allocation, runtime directories, and credential provisioning. Do not launch
bare server/client processes, reconstruct managed paths, manually allocate their
ports, or stop a process found only by its name.

Prefer the connected `atrinik` MCP for guidance/navigation using an explicit
Classic profile and component. Compare its source commit with the local checkout
and read returned resources. Continue incomplete queries with narrower scopes or
their cursor. For live identity, dirty files, commands, and authority, inspect the
local wrapper and checkout. The plugin does not authorize starting services or
altering resources.

Resolve a complete, isolated profile derived from `classic`. Select one Classic
physical worktree consistently across its components and the matching content,
sound, and resource providers. Use the current wrapper's procedures when creating
or selecting it. Existing resource bindings, permissions, leases, and build-plan
checks apply at the operation that uses them; a previous handoff is not a fence.

Confirm prerequisites appropriate to the requested proof: affected builds/tests,
available content, runtime libraries, a usable display/GPU for interactive client
checks, and audio output for audible checks. Do not infer those capabilities from
a successful configure or a server log. State a real missing prerequisite and
continue unaffected checks; never present an unobserved behavior as passing.

Use a task-specific `NAME` for both topology and scenario, distinct from concurrent
work. Verify the name is unused or currently owned by this task before mutation.
Never reuse another task's account/player state. Replace `PROFILE` and `NAME` in
the examples with the resolved values; run wrapper commands at the wrapper root.

## Provision an isolated player scenario

For gameplay requiring a player, use the wrapper's offline provisioning path:

```sh
./atrinik profile show PROFILE --json
./atrinik scenario create NAME --profile PROFILE --preset basic-player
./atrinik scenario show NAME --json
```

Read the returned state coordinate; the basic scenario convention is
`scenario-NAME`. Use the returned value if it differs. The supervised client can
log in using the scenario automatically. `./atrinik scenario credentials NAME`
is a private local diagnostic only when needed: never put its output in chat,
logs, screenshots, committed fixtures, issues, or a handoff. Do not replace that
mechanism with passwords in arguments or hand-edited account files.

When no pre-provisioned player is needed, the wrapper's `--temporary-state` mode
can provide an isolated runtime instead; inspect its resolved topology and use
the exact state choice consistently. Do not apply scenario commands to a temporary
state that has no scenario.

## Start, observe, and stop the owned topology

For the player scenario above, inspect the resolved services and state before
starting them:

```sh
./atrinik topology show PROFILE --state scenario-NAME --json
./atrinik up --name NAME --profile PROFILE --state scenario-NAME
./atrinik ps NAME --json
./atrinik logs NAME server --tail 200
./atrinik logs NAME client --tail 200
```

Between inspection and mutation, recheck applicable live ownership/authority
requirements. If the wrapper denies an operation, preserve its reason and repair
only within the task's authority; do not bypass it with direct processes or file
edits. Do not proceed past a failed prerequisite or claim a failed start succeeded.

Confirm the expected services are healthy, then perform the planned feature
action. Observe the result through the actual client/server path. Capture only
the minimal nonsecret evidence needed to distinguish the expected behavior from
the prior failure. For connection changes include reconnect; for persistence
changes include the authorized save/restart/load cycle on owned state. Live
rendering or sound claims need appropriate visual or audible evidence.

Asset verification follows the actual transport: the server stages immutable
asset bytes and size/digest metadata temporarily, independent of transport.
Authenticated QUIC delivers game data and client map/resource assets. An optional
`http_url` refers to an externally operated origin. Do not add a bundled HTTP
server or treat temporary asset staging as permanent player/runtime storage.

Inspect bounded logs again when the feature action warrants it. End the run even
after a failed feature check, but stop only the topology still owned by this task:

```sh
./atrinik down NAME
./atrinik ps NAME --json
```

If startup failed partway, inspect wrapper state and use its cleanup path for
owned residual resources. `./atrinik scenario reset NAME` is optional destructive
reprovisioning: use it only for an owned, stopped scenario when a fresh fixture is
needed and the reset is within scope. It is not a general cleanup command. Shared
or uncertain ownership is a reason to leave the state intact and report it.

## Deliver reproducible evidence

Include the resolved worktree/profile, topology and scenario names, state,
prerequisites, expected behavior and actual result. Give the exact `topology show`,
`up`, `ps`, bounded `logs`, and `down` commands used so another authorized operator
can reproduce the run. Say whether cleanup completed and whether state was
retained. Sanitize logs before sharing them; omit credentials and private local
metadata. Separate test success, process health, and observed feature results.
