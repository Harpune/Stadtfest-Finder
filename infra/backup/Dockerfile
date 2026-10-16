# Backup job of the production stack (ADR 0021), image stadtfest-backup (build context infra/backup).
# Daily: pg_dump of the database and a mirror of the image bucket (rclone over the S3 API) into an
# encrypted restic repository on the Hetzner Storage Box (sftp), retention BACKUP_KEEP_WITHIN.
FROM restic/restic:0.19.0 AS restic
FROM rclone/rclone:1.73.0 AS rclone

FROM postgres:17-alpine
RUN apk add --no-cache openssh-client tzdata \
 && adduser -D -u 10001 backup \
 && mkdir -p /cache /home/backup/.config/rclone \
 && touch /home/backup/.config/rclone/rclone.conf \
 && chown -R backup:backup /cache /home/backup/.config
COPY --from=restic /usr/bin/restic /usr/local/bin/restic
COPY --from=rclone /usr/local/bin/rclone /usr/local/bin/rclone
COPY --chmod=0755 backup.sh run.sh /usr/local/bin/
ENV RESTIC_CACHE_DIR=/cache/restic \
    BACKUP_TIME=02:30 \
    BACKUP_KEEP_WITHIN=30d
USER backup
WORKDIR /home/backup
HEALTHCHECK --interval=5m --timeout=10s --retries=1 CMD ["/usr/local/bin/backup.sh", "health"]
ENTRYPOINT ["/usr/local/bin/run.sh"]
