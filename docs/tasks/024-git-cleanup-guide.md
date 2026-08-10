# Git Repository Cleanup Guide (Open-Source Preparation)

Use this guide to audit and, only when necessary, rewrite the Git history before
making Apelios public. Work slowly: a history rewrite changes commit IDs and can
disrupt every existing clone.

This guide changes Git history only. A complete open-source review must also cover
licensing, dependency licenses, documentation, security reporting, CI, and release
configuration.

> **Important:** Read the entire guide before running any destructive command. Do
> not copy the commands unchanged: replace every placeholder and verify it first.

## 1. Decide what will be published

Write down the exact publication scope before inspecting or rewriting anything:

- repository and remote URL;
- branch or branches to publish (normally only `main`);
- tags to publish;
- branches and tags that must remain private;
- files, strings, identities, or generated artifacts that must be removed.

Do not use `git push --all` for publication. It can expose local backup, prototype,
or personal branches.

## 2. Prepare safely

### 2.1 Freeze repository changes

Coordinate with collaborators so nobody pushes during the cleanup. Confirm that
the working tree is clean:

```bash
git status --short --branch
git remote -v
git branch --all
git tag --list
```

Commit or deliberately preserve any uncommitted work before continuing.

### 2.2 Create two independent backups

Keep the normal working copy untouched. From its parent directory, create a
filesystem backup and a mirror backup:

```bash
cd /path/to/parent
cp -a apelios apelios-backup-YYYYMMDD
git clone --mirror /path/to/apelios apelios-backup-YYYYMMDD.git
```

Verify both backups:

```bash
test -d apelios-backup-YYYYMMDD/.git
git -C apelios-backup-YYYYMMDD.git fsck --full
```

Store the backups somewhere private. Do not push a backup branch or mirror to the
public remote.

### 2.3 Create a disposable cleanup clone

Perform history rewriting in a fresh clone, not in the everyday working copy:

```bash
git clone --mirror <PRIVATE_REMOTE_URL> apelios-cleanup.git
cd apelios-cleanup.git
git remote -v
git show-ref
```

A mirror contains all remote branches and tags, so audit all of them even if only
`main` will be published.

Install `git-filter-repo` using your preferred isolated tool installer, for
example:

```bash
pipx install git-filter-repo
git filter-repo --version
```

## 3. Audit the repository

### 3.1 Inventory all paths ever committed

```bash
git log --all --name-only --format= | sort -u
```

Look for raw benchmark results, archives, database dumps, environment files,
credentials, private notes, personal data, generated assets, and editor or IDE
files.

### 3.2 Find the largest historical blobs

```bash
git rev-list --objects --all |
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' |
  awk '$1 == "blob" {print $3, $4}' |
  sort -nr |
  head -50
```

The first column is the size in bytes. GitHub rejects individual files larger
than 100 MiB and recommends keeping repositories substantially smaller than its
hard limits. Large generated artifacts should normally be regenerated or stored
as release assets instead of being committed.

### 3.3 Search current files

Use a secret scanner if one is available, and supplement it with targeted searches:

```bash
rg -n --hidden \
  --glob '!.git/**' \
  '(password|passwd|secret|api[_-]?key|access[_-]?token|private[_-]?key)'
```

Also search for machine-specific paths and personal identifiers:

```bash
rg -n --hidden --glob '!.git/**' '(/home/|/Users/|C:\\Users\\)'
rg -n --hidden --glob '!.git/**' '<PERSONAL_EMAIL_OR_NAME>'
```

Review every match manually. Variable names such as `password` are not themselves
secrets, while an innocent-looking token can still be sensitive.

### 3.4 Search history for known strings

`git log -S` finds commits where the number of occurrences changed:

```bash
git log --all -i -S '<KNOWN_SECRET_OR_IDENTIFIER>' --oneline --patch
```

This is useful for known values, but it is not a complete secret scan.

### 3.5 Review metadata and publication files

Inspect:

```bash
git log --all --format='%h %an <%ae> %s'
git shortlog --summary --email --all
git status --ignored --short
```

Confirm that author identities are acceptable to publish and that `.gitignore`
excludes local configuration, credentials, logs, coverage data, raw performance
results, virtual environments, and build output.

Before proceeding, record findings in a private checklist. Never put actual secret
values into that checklist or a commit message.

## 4. Respond to exposed credentials first

If a credential has ever been committed:

1. revoke or rotate it immediately;
2. remove it from the current files;
3. rewrite history if the old value should not remain visible;
4. check CI variables, releases, issues, pull requests, forks, caches, and logs;
5. verify that the replacement credential was never committed.

History rewriting does **not** make a credential safe again. Treat every committed
credential as compromised even if the repository was private.

## 5. Rewrite history only when required

Make one planned `git filter-repo` invocation where practical. Repeated rewrites
make review harder.

### 5.1 Remove complete paths from every ref

Create a file containing one exact repository-relative path per line:

```text
results/e2e/large-result.csv
path/to/private-file.txt
```

Then run:

```bash
git filter-repo --invert-paths --paths-from-file paths-to-remove.txt
```

Use `--path-glob` only when the pattern has been reviewed carefully. A broad glob
can remove more history than intended.

### 5.2 Replace sensitive text while keeping files

Create `replacements.txt` outside the repository. Follow the `git-filter-repo`
replacement format, for example:

```text
literal:OLD_VALUE==>REDACTED
glob:prefix-*==>REDACTED
regex:example[0-9]+==>REDACTED
```

Run:

```bash
git filter-repo --replace-text /private/path/replacements.txt
```

Do not commit the replacement file. Delete it securely after the audit if it
contains sensitive values.

### 5.3 Removing a commit is exceptional

Do not use an `--invert-paths --path-glob '*'` command to “remove a commit”; that
removes file content and can corrupt the history.

If a commit only introduced unwanted files or strings, remove those paths or
replace those strings across history instead. If the commit itself must disappear
while later changes remain, stop and design the rewrite with an experienced
reviewer using `git rebase --rebase-merges` or a tested commit-callback. This is
case-specific and should not be reduced to a generic copy-paste command.

### 5.4 Check remotes after filtering

`git filter-repo` may remove the `origin` remote as a safety measure. Inspect it:

```bash
git remote -v
```

If it was removed, restore the correct private remote only after verification:

```bash
git remote add origin <PRIVATE_REMOTE_URL>
```

## 6. Verify the rewritten repository

Do not push until every check passes.

### 6.1 Verify repository integrity and refs

```bash
git fsck --full
git show-ref
git log --oneline --decorate --graph --all
```

Compare the resulting branch tips and tags with the publication scope from step 1.

### 6.2 Repeat the complete audit

Repeat all searches from section 3, including the path inventory, large-blob list,
secret scan, identity review, and known-string searches. Confirm explicitly that
every recorded finding is resolved.

For a known removed path:

```bash
git log --all -- path/to/removed-file
```

For a known removed value:

```bash
git log --all -i -S '<REMOVED_VALUE>' --oneline --patch
```

Both commands should produce no relevant match.

### 6.3 Test a normal checkout

Clone the cleaned mirror locally into a temporary directory:

```bash
cd /tmp
git clone /path/to/apelios-cleanup.git apelios-verify
cd apelios-verify
git status --short --branch
```

Follow the documented setup from scratch, run the full automated test suite, build
the documentation, and regenerate representative performance plots. This catches
files that were accidentally removed from history or silently relied on a local
machine path.

## 7. Publish deliberately

### 7.1 Prefer a new public repository when possible

The safest publication flow is to push only the reviewed branch and intentional
tags to a new, empty public repository:

```bash
git remote add public <NEW_PUBLIC_REMOTE_URL>
git push public refs/heads/main:refs/heads/main
git push public <TAG_NAME>
```

Push tags individually or from a reviewed list. Do not push `--mirror`, `--all`,
backup refs, pull-request refs, or every tag by default.

### 7.2 Replacing history on an existing remote

Only do this after freezing pushes. Record the current remote tip without fetching
it into the rewritten mirror:

```bash
git ls-remote origin refs/heads/main
```

Review `main` locally and compare it with the pre-cleanup backup. Then use the
recorded remote object ID as an explicit lease:

```bash
git log --oneline --decorate main
git push \
  --force-with-lease=refs/heads/main:<OLD_REMOTE_MAIN_OID> \
  origin refs/heads/main:refs/heads/main
```

In a mirror clone, a normal fetch can map remote refs directly onto local refs and
undo the rewrite. The explicit lease protects against overwriting a branch that
changed after its object ID was recorded.

If the lease fails, stop. Someone may have pushed after the cleanup began. Do not
replace `--force-with-lease` with `--force` until the new remote state has been
understood and reconciled.

Tell all collaborators that commit IDs changed and require them to re-clone or
carefully reset their clones. Open pull requests based on the old history may need
to be recreated.

## 8. Verify the published repository

Clone from the final public URL into a new directory:

```bash
cd /tmp
git clone <PUBLIC_REMOTE_URL> apelios-public-verify
cd apelios-public-verify
git remote -v
git branch --all
git tag --list
```

Then:

- repeat the secret, path, size, and identity checks;
- run the documented installation and full test suite;
- inspect the repository through the hosting website;
- verify that only intended branches and tags exist;
- inspect releases, actions artifacts, issues, pull requests, wikis, packages, and
  cached pages for sensitive material;
- confirm branch protection, required checks, dependency alerts, and secret
  scanning settings;
- keep the old repository private until this review is complete.

## 9. Recovery

If verification fails, do not keep layering unreviewed fixes onto a bad rewrite.
Discard the disposable cleanup clone, return to the untouched backup, update the
private findings checklist, and repeat the procedure.

If incorrect history was already pushed, immediately make the repository private,
notify collaborators, rotate any exposed credentials, and restore or redo the
history from the private mirror backup. Hosting-provider caches and existing clones
may retain removed data, so contact the provider when sensitive data was exposed.

Keep the private backups until the public repository has been verified and all
collaborators have migrated. Dispose of them deliberately afterward; they still
contain everything removed from public history.

## Final go/no-go checklist

Publish only when every item is true:

- [ ] Exact public branches and tags are documented.
- [ ] Files and history have been scanned for secrets and personal data.
- [ ] Every discovered credential has been revoked or rotated.
- [ ] Raw results, generated data, and machine-specific paths are excluded.
- [ ] No unintended large blobs remain in reachable public history.
- [ ] Commit author names and email addresses are acceptable to publish.
- [ ] Repository integrity checks pass.
- [ ] A fresh clone installs, tests, builds, and regenerates outputs successfully.
- [ ] Licensing and dependency-license review is complete.
- [ ] Only reviewed refs will be pushed.
- [ ] The published repository has been cloned and audited again.
- [ ] Private backups remain available until final sign-off.

---

*Last updated: 2026-08-07*
