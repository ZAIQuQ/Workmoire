# Versioning and release workflow

The established repository is [ZAIQuQ/Workmoire](https://github.com/ZAIQuQ/Workmoire),
branch `main`. The owner has authorized GitHub synchronization after each round
of substantial work is tested, deployed and verified. This is a standing
maintenance instruction; do not stop at a local commit or ask for push permission
again. Never force-push, rewrite published history, or replace unrelated remote
changes. Minor related fixes may be grouped into the same release.

## Before publication

Enabling AI paper analysis requires the [90% acceptance gate](paper-acceptance.md) for the exact deployed profile. Releases that keep analysis disabled can ship with the regular checks.

1. Fetch `origin/main` and integrate upstream changes. Preserve both histories.
2. Update the package version, lockfile, changelog, and both README languages.
3. Use Node 22 and run `npm ci`. If frontend assets changed, run `npm run build` and include the generated bundles and compressed files in the commit. Run `make preflight` on the exact commit. It checks source boundaries, generated assets, syntax, and backend and command tests. Use `npm run test:browser -- -g <pattern>` for focused local browser checks.
4. Push the commit to `main` and wait for GitHub quality to pass. The source checks and the two browser suites run in parallel. The tag reuses the successful `main` run for the same commit.
5. Back up private data, deploy the checked commit, write its `REVISION`, and verify both services. Publish the release from that commit.

## Prepare and publish

If needed, authenticate GitHub CLI using the browser. Workflow changes require the `workflow` scope.

```bash
gh auth login --hostname github.com --git-protocol https --web --scopes workflow
gh auth setup-git
```

Prepare the committed version.

```bash
python3 scripts/publish_release.py --prepare
```

The script waits for the quality workflow triggered by the push to `main`. If it fails, use the failed job's trace and logs to diagnose it. Commit a fix when the source or test is at fault. For a reported runner or network failure, rerun the failed job on the same commit.

After deploying and verifying that commit, publish the tag and GitHub Release.

```bash
python3 scripts/publish_release.py \
  --deployment-dir /path/to/workmoire \
  --share-deployment-dir /opt/workmoire-share
```

Omit the sharing argument when that service is absent. Publication requires a clean checkout, a successful `main` quality run for the exact commit, matching deployed revisions, and healthy services. Release tags stay immutable.

## Version UI

The sidebar badge and About panel read the deployed `package.json` version and
`REVISION`, not a guessed version from GitHub. Only opening About requests an
update check. The authenticated endpoint fetches the fixed public GitHub release
URL, sends no document/account data, and caches successful results for fifteen
minutes and failures for one minute. Checks have a four-second timeout and a
bounded response. No Release, an unavailable network and a newer version are
separate states. The GitHub project, latest release and changelog links remain
usable when checking is unavailable.
