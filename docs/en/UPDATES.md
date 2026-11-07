# Data, backups, updates, migrations and rollback

## Where the data is

Code and data are apart. Data lives in `~/Sol-83-data` by default; `SOL83_HOME` (or the older `GEMINI_HOME`) selects another folder: `state/gemini.db` (SQLite: projects, queue, events, versions, questions, plan revisions, usage, catalog), `projects/` (repositories Sol-83 created and GitHub clones), `worktrees/<id>` (agents' folders), `worktrees/<id>-testy` (the user folder with the chosen version, used by RUN), `runs/<id>/` (engine runs and logs), `config/`. Repositories you gave as a source stay where they are; Sol-83 only adds a `gemini/<id>` branch, version tags and worktrees there.

## Backup

Stop the panel and let projects finish their turns, then:

```bash
cp -cRp ~/Sol-83-data ~/Sol-83-backup-$(date +%Y%m%d)
```

On macOS `cp -c` makes an APFS clone that takes no space until files change: it protects against program errors and mistakes, not against disk failure (use Time Machine or another disk for that). On Linux use `cp -a`.

## Updating the code

```bash
git pull
```

```bash
rm -rf vendor/duet && ./bin/setup
```

The database schema updates itself at start (new tables and columns only, nothing removed). Older projects get a key (PRn/yy) and a language read from their task on first start.

## Migrating an older installation

Versions before OpenBeta kept data next to the code. Move it with:

```bash
./sol83 migrate --from <old app folder> --dry-run
```

```bash
./sol83 migrate --from <old app folder>
```

It refuses while old engines run or when the target is not empty; copies the data (APFS clones on macOS, SQLite backup for the database); rewrites paths in the database, run configurations and run states (historical event texts stay as written); repairs worktree links; compares record counts and writes `MIGRATION.json`. The source is not changed, except that worktrees of your own repositories outside the data folder get their back-link updated; `--trial` rehearses on a copy without that.

## Rolling back

1. Stop the panel.
2. Move the current data aside: `mv ~/Sol-83-data ~/Sol-83-data.rejected`.
3. Restore a backup: `cp -cRp ~/Sol-83-backup-YYYYMMDD ~/Sol-83-data`.
4. To go back to older code: `git checkout <tag or commit>`, then `rm -rf vendor/duet && ./bin/setup`.
5. To go back to a pre-OpenBeta installation, start the old code from its own folder: it uses its own data, not `~/Sol-83-data`.
