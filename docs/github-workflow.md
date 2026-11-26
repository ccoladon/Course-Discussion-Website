# GitHub workflow

## Commit messages

- Short imperative subject (under 70 chars): `Fix 0006 migration: null FK refs before deleting rows`.
- Body is optional. For trivial or self-explanatory changes, subject-only is fine.
- When Claude paired on the change, add a co-author trailer:

  ```
  Co-Authored-By: Claude <noreply@anthropic.com>
  ```

- Prefer new commits over `--amend` once anything has been pushed.

## When to commit

Commit and push automatically when a change is complete and verified. Keep the commit focused on that change; don't sweep in unrelated working-tree edits.

## Pull requests

Use the `gh` CLI for everything PR-related:

```bash
gh pr create --title "..." --body "$(cat <<'EOF'
## Summary
- bullets

## Test plan
- [ ] item
EOF
)"
```

Keep titles under 70 chars. Put detail in the body.

## MCP: GitHub server

If you want Claude to interact with GitHub via MCP, configure the server in `.mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    }
  }
}
```

The `${VAR}` form makes the MCP runtime read the token from the shell env, so the secret never lives in the repo. Set the var in your shell rc or a local-only `.envrc` (gitignored).

⚠️ Never paste a literal PAT into `.mcp.json` — it ends up in git history. See `docs/secrets-and-env.md` for the cleanup pattern.

## Branch protection (recommended)

- Require PRs for `main`/`master`.
- Require status checks if you wire up CI later.
- Disable force-pushes to the default branch.

Solo projects often commit directly to `master` — that's a project choice, not a stack convention. See `PROJECT.md` for this project's branch policy.
