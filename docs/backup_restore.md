# Backup and Restore

This project stores production state in two places:

- PostgreSQL database: users, sessions, messages, notifications, spots, and metadata.
- Media files: profile pictures and uploaded spot photos.

Both must be backed up together. A database-only backup is incomplete because user
profiles and spot galleries may reference files from the media volume.

## Recovery Targets

- RPO: at most 24 hours of data loss for a small production deployment.
- RTO: restore into a fresh environment within 2 hours.

Adjust these targets before running a real production system with paying users.

## Create a Backup

Run this from the project root while Docker Compose services are running:

```bash
scripts/backup.sh
```

The script creates:

```text
backups/YYYYmmdd-HHMMSS/
  database.sql.gz
  media.tar.gz
  manifest.txt
```

The backup directory is created with `0700` permissions. Move completed backups to
encrypted off-server storage. Do not keep the only copy on the application host.

## Restore a Backup

Restore is destructive for the target database and media directory. Run it only
against the environment you intentionally want to replace.

```bash
CONFIRM_RESTORE=YES scripts/restore.sh backups/YYYYmmdd-HHMMSS
```

The script:

- recreates the PostgreSQL `public` schema,
- imports `database.sql.gz`,
- replaces `/app/media` inside the web container with `media.tar.gz`.

## Verification After Restore

After restore, verify:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py migrate --check
```

Then manually inspect:

- login with a known non-admin user,
- profile picture rendering,
- spot gallery rendering,
- direct conversation list,
- session details and participant lists,
- notifications list.

## Retention

Recommended minimum retention:

- daily backups for 14 days,
- weekly backups for 8 weeks,
- monthly backups for 6 months.

Backups should be encrypted at rest and stored in a location that cannot be deleted
from the production application host with the same credentials.

## Security Notes

- Never commit backup files.
- Never store backups in `media/`, `staticfiles/`, or the repository root long term.
- Rotate `SECRET_KEY`, database passwords, and any external API keys if a backup is
  exposed.
- Test restore regularly into an isolated environment, not into production.
