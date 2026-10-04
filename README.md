# Atrinik agent integrations

Public, MIT-licensed, portable Agent Skills for Atrinik development. Codex users
can install them from this repository's plugin marketplace, which contains
`atrinik-development`; its plugin package is the single canonical copy under
`plugins/atrinik-development/`.

## Install with Codex

Add the public marketplace and install the plugin:

```sh
codex plugin marketplace add atrinik/agent-integrations
codex plugin add atrinik-development@atrinik
```

Start a new Codex session after installation. To inspect configured sources or
the installed plugin, use `codex plugin marketplace list` and
`codex plugin list`. These command forms follow the official OpenAI
[Codex developer command reference][codex-commands].

### Migrate from the private marketplace

Install the public plugin first, then remove the old private copy after you have
confirmed the public installation:

```sh
codex plugin add atrinik-development@atrinik
codex plugin list
codex plugin remove atrinik-development@atrinik-private
```

The two installations share the plugin name but have different marketplace
identities. Keep the marketplace suffix on migration commands so Codex changes
the intended installation. Removing the retired installation only updates
local Codex configuration; it does not import or expose history from the
deleted private repository that formerly used this repository name.

## Atrinik MCP is separate

The Atrinik MCP implementation and configuration remain in
[`atrinik/atrinik`](https://github.com/atrinik/atrinik). This plugin contains
skills and public reference documents only. It does not contain, launch,
install, authenticate, or configure an MCP server. Configure an existing
Atrinik MCP service separately when you want source navigation tools; the
skills continue to work without it.

## Validate

The ordinary checks are local and require no credentials, network access,
Atrinik checkout, MCP service, or private repository:

```sh
python3 -m unittest discover -v
python3 -W error -m compileall -q -f tests
git diff --check
```

See [provenance](PROVENANCE.md) for the public upstream revision and the
documented migration edits.

[codex-commands]: https://learn.chatgpt.com/docs/developer-commands
