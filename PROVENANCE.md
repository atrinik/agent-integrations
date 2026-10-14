# Provenance

This repository is MIT licensed. The twelve Atrinik workflow skills and five
shared documents were imported from the public `atrinik/atrinik` repository at
the full revision recorded in the installed plugin's
[`provenance.json`](plugins/atrinik-development/provenance.json), under that
repository's MIT license. The JSON record retains the original Git tree/blob
identities and the explicit portability and authority edits made during
migration.

No Git history or source material from the deleted private repository that
formerly used the `atrinik/agent-integrations` name is part of this public
repository. This public repository reuses only that name. The deleted
repository was used only as an already-reviewed package-shape reference; it is
not a public provenance source.

The operational delivery-ledger helper remains owned by the Atrinik wrapper and
is not distributed by this plugin. The public guidance selects the helper only
inside an exact accepted wrapper root, preferring its current `scripts/` path
and retaining the historical skill path solely for accepted older wrappers.

The three Classic skills are new MIT work and have separate authorship entries
in the plugin provenance record; they do not inherit the imported wrapper
provenance.

The `local_authored_updates` records distinguish later provider-authored edits
from the original wrapper import. Each records an already-public immutable
provider revision, exact source/destination blobs, the public baseline and local
transformations, and the contemporaneous provider MIT license. These snapshots
do not claim a new wrapper origin, alter the original import identities, or pin
the revision of the provenance record itself.

Package validation resolves each local source, baseline and license claim from
the provider's actual Git objects without network access. Missing commits or
blobs fail validation; CI checks out full history with credentials disabled.
Because squash merges do not retain PR commits as main ancestors, CI also
fetches the validated full local source/baseline commit IDs from the fixed
public provider repository before running offline tests. Fetch failure fails
validation; it does not substitute current files for the recorded Git objects.

For external `current_file_updates`, CI shallow-fetches each validated full
revision from the fixed public wrapper repository. Offline validation verifies
the source and MIT license blobs, reconstructs the declared link edits, and
checks every historical destination blob. It compares each destination's final
update with the packaged bytes while preserving earlier chain records.
