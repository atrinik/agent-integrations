# Contributing

Keep reusable skill content in the canonical plugin directory. Do not add a
second generated package, MCP payload, launcher, credentials, private records,
host state, or material copied from a private repository's history.

Preserve skill invocation policies and the authority boundaries of local
Atrinik repositories. Tests and examples must be synthetic and run without
network access. Record upstream rights and intentional migration edits in
`plugins/atrinik-development/provenance.json` when imported content changes.

Use a Conventional Commits pull-request title:
`type(optional-scope): concise description`. Add `!` before the colon only when
the author explicitly requests a breaking contract change. Before opening a
pull request, run the validation commands from the README. Keep the `Required
checks` and `Conventional PR title` job names stable.
