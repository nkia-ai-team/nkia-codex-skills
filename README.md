# NKIA Codex Skills

Codex marketplace for NKIA-AI workflow skills.

## Skills

| Skill | Purpose |
|---|---|
| `$feature` | Create or update parent Linear feature issues |
| `$task` | Create executable child task issues |
| `$start` | Start a task and create the branch |
| `$ship` | Push PR/MR and run review loop |
| `$finish` | Validate evidence and roll up parent feature status |
| `$weekly` | Prepare and write the weekly work report |

## Layout

```text
.agents/plugins/marketplace.json
plugins/nkia-codex-skills/.codex-plugin/plugin.json
plugins/nkia-codex-skills/skills/
```

## Local Install Fallback

If marketplace install is unavailable, copy skills directly:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R plugins/nkia-codex-skills/skills/* "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Restart Codex after installing.

## Weekly Report Auth Note

`$weekly` uses `gws` for Google Sheets and Calendar. Each teammate must configure their own `~/.config/gws/client_secret.json` and run `gws auth login`; OAuth tokens stay local to the user machine.
