# Development Workflow

> Baseline branch: `master`
> Feature work must branch from `master` and merge back only after verification.

## Branch Roles

| Branch | Role |
|--------|------|
| `master` | Stable baseline. Contains merged, verified vertical slices only. |
| `feature/*` | Short-lived development branches for one spec or feature. |

Do not commit unverified experiments directly to `master`.

## Standard Flow

1. **Sync baseline**

   ```bash
   git checkout master
   git pull origin master
   ```

2. **Create a feature branch**

   ```bash
   git checkout -b feature/<short-name>
   ```

   Example: `feature/phase-4-memory-skill-drafts`

3. **Develop with spec + TDD**

   - Update or add the phase spec under `specs/` before behavior changes.
   - Write failing tests, implement, make tests pass.
   - Keep runtime artifacts under `.agent-factory/` (never commit).

4. **Verify before merge**

   ```bash
   python -m pytest tests/unit -v
   ```

   Add integration checks when the feature needs them. Do not merge while tests fail.

5. **Merge to baseline**

   ```bash
   git checkout master
   git pull origin master
   git merge --no-ff feature/<short-name>
   git push origin master
   ```

   Prefer `--no-ff` merge commits so each feature slice stays visible in history.

6. **Clean up**

   ```bash
   git branch -d feature/<short-name>
   ```

## Pull Requests (optional)

When using GitHub PRs instead of local merge:

- Open PR: `feature/<short-name>` → `master`
- PR description must list spec link, test command, and manual demo steps if any.
- Merge only after CI/local tests pass and review is done.

## Agent / Contributor Checklist

- [ ] Branched from latest `master`
- [ ] Spec updated for architecture or behavior changes
- [ ] `python -m pytest tests/unit -v` passes
- [ ] No `.agent-factory/` or secret files staged
- [ ] Spec handoff / TODO section updated
