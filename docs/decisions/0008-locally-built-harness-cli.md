# 0008 Locally Built Harness CLI For glibc 2.34 Sandbox

Date: 2026-07-19

## Status

Accepted

## Context

This project runs inside a Hyperagent sandbox on Amazon Linux 2023
(glibc 2.34, x86_64). The Harness installer downloaded and
checksum-verified the pinned release binary `harness-cli-v0.1.17`
(linux-x64), but that asset is built on newer runners and requires
glibc >= 2.39, so it fails to execute here:

```
/lib64/libc.so.6: version 'GLIBC_2.39' not found
```

`scripts/bootstrap-harness.sh` only requires that `scripts/bin/harness-cli`
is executable and that `--version` matches `scripts/harness-cli-release-tag`;
it does not re-verify the release checksum for installed projects.

## Decision

Build `harness-cli` from the upstream source tarball at the exact pinned tag
`harness-cli-v0.1.17` (Rust 1.95.0, `cargo build --release --locked`) and
install the resulting binary at `scripts/bin/harness-cli`. The build is done
outside the repository root so bootstrap does not misclassify this consumer
repo as a Harness source checkout.

## Alternatives Considered

1. Use an older release asset — rejected: all published assets are built on
   runners with glibc >= 2.35, none run on glibc 2.34.
2. Patch or sideload a newer glibc — rejected: fragile and invasive for a
   sandbox.
3. Skip the CLI entirely — rejected: the CLI is the main Harness tool and
   stable command path.

## Consequences

Positive:

- Same version (0.1.17) and same source as the pinned release; bootstrap and
  all `harness-cli` commands work in this sandbox.

Tradeoffs:

- The local binary's checksum differs from the published `.sha256` asset.
- Any `--upgrade-cli` install or CLI re-download will restore an incompatible
  binary; the rebuild recipe in `AGENTS.md` (Local Project Notes) must be
  re-run afterwards.

## Follow-Up

- When upstream publishes a musl/static or older-glibc Linux asset, switch
  back to the verified release binary and supersede this decision.
