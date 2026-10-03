# Atrinik agent skills

Public, MIT-licensed agent skills for Atrinik development. The repository is a
Codex plugin marketplace containing `atrinik-development`; its plugin package is
the single canonical copy under `plugins/atrinik-development/`.

## Install with Codex

Add the public marketplace and install the plugin:

```sh
codex plugin marketplace add atrinik/agent-skills
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
the intended installation. Removing the old plugin does not change the
visibility of `atrinik/agent-integrations` or publish any of its history.

## Atrinik MCP is separate

This plugin contains skills and public reference documents only. It does not
contain, launch, install, authenticate, or configure an MCP server. Configure an
existing Atrinik MCP service separately when you want source navigation tools;
the skills continue to work without it.

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
