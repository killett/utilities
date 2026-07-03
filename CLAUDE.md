# Project: utilities

A collection of independent standalone scripts (one utility per file).

## Commit message convention

This repo holds multiple unrelated scripts, so commit messages must
identify which script they concern. Prefix the usual Conventional
Commit message with the name of the script the commit works on,
followed by `: `:

```
<script-name>: <type>: <description>
```

where `<type>` is the normal Conventional Commit type (`feat`, `fix`,
`chore`, `test`, `docs`, `refactor`, etc.). Examples:

- `clean-caches.sh: feat: add rehash hint after install`
- `download_file.py: chore: bump default timeout`
- `check_internet.py: fix: handle IPv6-only hosts`

Use the exact filename (including extension) as the prefix. A commit
that spans no single script (repo-wide config, licensing, etc.) may
omit the script prefix and use a bare `<type>: <description>`.
