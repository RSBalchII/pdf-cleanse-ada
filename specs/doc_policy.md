# Documentation Policy

## Allowed Documentation Locations

All project documentation **MUST** live in one of these locations:

| Location | Purpose |
|----------|---------|
| `README.md` | Project overview, quick start, user-facing documentation |
| `CHANGELOG.md` | Chronological record of changes, releases, and notable events |
| `specs/` | Technical specifications, architecture diagrams, pain points, standards, tasks, plans |

## Auth Endpoints (OAuth)

The OAuth server runs on port 3457 and is proxied through the main server:

| Endpoint | Purpose |
|----------|---------|
| `GET /auth/login` | Redirect to Adobe OAuth |
| `GET /auth/callback` | Handle OAuth callback |
| `GET /auth/logout` | Log out |
| `GET /auth/status` | Check auth status |
| `GET /auth/token` | Get access token (internal) |

## Prohibited

- ❌ Documentation scattered in arbitrary markdown files at the project root
- ❌ "Notes", "TODO", "IDEAS", "LEARNINGS" files in the root directory
- ❌ Documentation inside code directories (outside `specs/`)
- ❌ Multiple README files (`README_old.md`, `README_backup.md`, etc.)

## Specs Directory Structure

```
specs/
├── spec.md            # Architecture diagrams and visual documentation
├── tasks.md           # Current task tracking and status
├── plan.md            # Project roadmap and planning
├── doc_policy.md      # This file
└── standards/         # Numbered standards documents
    ├── 001-*.md       # Pain points, fixes, and definitive standards
    ├── 002-*.md
    └── ...
```

## Standards Numbering

Each file in `specs/standards/` follows the format:

```
specs/standards/NNN-title.md
```

Where:
- `NNN` is a zero-padded 3-digit number (001, 002, 003...)
- `title` is a short kebab-case descriptor
- Each standard documents **one** pain point with its fix and the resulting definitive standard

## Adding New Standards

1. Identify the next available number in `specs/standards/`
2. Create `specs/standards/NNN-title.md`
3. Follow the standard template (see `001-pdf-lib-catalog-access.md` for format)

## Updating Existing Standards

- Edit the existing numbered file in place
- Do NOT create a new file for an update
- Reference the original number in commit messages

## Migration Rule

If documentation exists outside the allowed locations:
1. Move it to the correct location under `specs/`
2. Update references in other docs
3. Delete the straggler file
4. Commit with message: `docs: migrate <file> to specs/`
