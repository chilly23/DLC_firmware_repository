# Developing and releasing Nexatom

`main` contains the current app only. Each version is a commit/tag in history, rather than another folder inside the app. Work on a branch; merge actual changes into `main`; update VERSION and application metadata when completing a release.

## Meaningful commits

Commit coherent changes separately: input decoding, ownership/recovery, controller changes, UI changes, regression tests and documentation. Do not backdate contributions or repeatedly add/remove files to imitate development. Empty commits are not implementation work. The initial archive import is split by module and checkpoint, with its actual publication dates.

```bash
git switch main
git pull --ff-only
git switch -c version/1.18
# Work and verify each coherent change:
git add hardware tests
git commit -m "Handle the input change and its regression"
git push -u origin version/1.18
```

Use a pull request to review/merge. Start from an older version with `git switch -c my-fix v1.16`. Use `git switch --detach v1.16` only for inspecting that checkpoint. Downloading a tag gives one checkpoint, not all archived folders.

## Verification

Install requirements in a virtual environment. Run unit tests before pushing. GitHub Actions performs source checks on Windows and Linux; hardware injection tests are not physical GPIO certification.

```bash
python -m unittest discover -s tests -p "test_*.py"
python tests/verify_release.py --native
```

The standalone UI protection test uses the recorded base hashes when another version folder is absent. Archived reports describe their original runs; the history import does not silently claim old versions were tested again.

## Tag and distribute a completed release

Update VERSION, displayed application version, documentation and validation; verify the app. Merge into `main`, then make an annotated immutable tag:

```bash
git switch main
git pull --ff-only
git tag -a v1.18.0 -m "Nexatom v1.18.0"
git push origin main
git push origin v1.18.0
```

Create a GitHub Release at that tag. Attach a Windows ZIP containing just that release's source, assets, runtime and packages, plus its SHA256 checksum. Keep libraries' supplied licence notices in the bundle. Mark the completed release Latest. GitHub supplies source ZIP/tar archives for every tag automatically. Source Git excludes installed dependencies, calibration-generated state, logs, captures and caches.

For v1.17, `v1.17` is the exact source checkpoint import; `v1.17.0` is its publication with standalone test portability, repository guidance, CI and the separately supplied firmware sketch. Application behaviour is identical. Earlier local version folders have not been changed.

## Requested activity checkpoints

At the repository owner's explicit request, this publication includes labelled empty activity commits to reach 2,000 total commits. They contain no code changes, carry the actual publication date, and use `[skip ci]`. Version tags continue to identify real application checkpoints. This is a one-time activity batch, separate from normal development.
