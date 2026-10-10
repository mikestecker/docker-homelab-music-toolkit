# Worker teardown

Run this once AudioMuse's first full analysis finishes. It takes the temporary mini-PC worker offline and closes the database port that was opened for it. About 10 minutes. (Moved here from the separate AudioMuse Worker Teardown doc, Oct 7.)

## 1. Confirm the scan is finished

Don't stop the worker until all three of these are true. If you stop it partway through, it can use up the retries on whatever album it's holding.

- **Dashboard:** the `main_analysis` task shows **SUCCESS** and the Albums count equals the total (4,842 when it started).
- **Setup Wizard → Machine Learning Models:** the bars under MusiCNN, DCLAP and GTE Lyrics show five segments (Ready). The indexes are rebuilt at the very end of the run, after the last album.
- **Mini-PC worker is idle.** This should print nothing new for a few minutes:

```bash
# inside the LXC (pct enter <ctid>)
docker logs -f --tail 5 audiomuse-worker-minipc 2>&1 | grep "Analyzing track"
```

If the task ended as FAIL instead, start a new analysis from the main page and let it finish first. It skips everything already done.

## 2. Stop the mini-PC worker

Inside the LXC:

```bash
cd /opt/audiomuse-worker
docker compose down
```

Then on the Proxmox host, pick one:

```bash
# Keep it for the next big scan (costs ~32 GB of disk, nothing else)
pct shutdown <ctid>

# ...or remove it completely
pct shutdown <ctid> && pct destroy <ctid>
```

Not sure of the container ID? `pct list` shows it next to `audiomuse-worker`. It's already set not to start on boot, so a kept LXC stays off after a host reboot.

CPU check: after this, the host's `htop` should drop back to normal. Plex, Home Assistant and Scrypted get their 6 cores back.

## 3. Close the Postgres port on the NAS

Do this only after step 2, or the remote worker will keep retrying the connection.

In TrueNAS go to **Apps → audiomuse → Edit** and delete the `ports` block from the `postgres` service:

```yaml
  postgres:
    container_name: audiomuse-postgres
    # ports:            <- remove these two lines
    #   - '5432:5432'
    environment:
      - POSTGRES_USER=audiomuse
      ...
```

Save and redeploy. Flask and the NAS worker reach Postgres over the stack's internal network, so they don't need the port.

Check from the TrueNAS shell that it's closed and everything came back up:

```bash
sudo ss -ltn | grep ':5432'        # should print nothing
sudo docker ps --filter name=audiomuse --format '{{.Names}}  {{.Status}}'
```

All three containers (`audiomuse-flask`, `audiomuse-worker`, `audiomuse-postgres`) should show `Up`, and postgres should show `(healthy)`.

## 4. After teardown

The scan finishing is what everything else was waiting on.

- [ ] **Back up AudioMuse.** Go to **Administration → Backup and Restore** and make a backup now. If Navidrome's track IDs ever change, a backup saves you from redoing a multi-day scan.
- [ ] **Finish the Navidrome plugin settings.** As of Oct 7 it had no saved settings, so it was still pointed at the developer's default address. In Navidrome go to **Settings → Plugins → AudioMuse-AI** and set the API URL to `http://10.0.9.101:8000`. Add the API Token from AudioMuse's Setup Wizard, save, and make sure it's enabled. (Full plugin setup is in the Navidrome plugins tab.)
- [ ] **Test Instant Mix.** Run **Similar Song** on a track in the AudioMuse UI, then **Instant Mix** on the same track in Navidrome. Both should log a request:

```bash
sudo docker logs --tail 20 audiomuse-flask
sudo docker logs --tail 50 navidrome 2>&1 | grep audiomuseai
```

- [ ] **Turn on scheduled tasks.** In **Scheduled Tasks**, make sure the nightly 2am Analysis is enabled. It only picks up new albums, which the NAS worker handles fine alone. Move Radio Playlists off Saturday 3am (to Sunday `0 6 * * 0`, for example) so it doesn't collide with Clustering.
- [ ] **Run Clustering once** by hand if you want the mood playlists now instead of waiting for Saturday.

## 5. Next time

Only worth doing for another large batch, like a big import or a full re-analysis after a model change. Nightly runs don't need it.

If you kept the LXC, it's four steps:

1. On the NAS, add `ports: ['5432:5432']` back to the `postgres` service and redeploy.
2. On the Proxmox host: `pct start <ctid>`
3. In the LXC, pull the same image version the NAS runs and start it:

```bash
cd /opt/audiomuse-worker
docker compose pull && docker compose up -d
```

Pull the NAS image at the same time (`sudo docker pull ghcr.io/neptunehub/audiomuse-ai:latest`, then redeploy the app), so both workers match the database.

4. When it's done, run this tab again from step 1.

If you deleted the LXC, the full setup is in the chat from Oct 7: create the LXC with the Docker script, then `/opt/audiomuse-worker/.env` and `compose.yaml`.
