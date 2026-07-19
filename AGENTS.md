# Agent Instructions

<!-- HARNESS:BEGIN -->
## Harness

Choose the request class before any Harness operation.

- When the requested outcome is only an answer, explanation, review, diagnosis,
  plan, or status report: inspect only the material needed to respond. Keep the
  task read-only. Do not bootstrap, initialize or migrate a database, record
  intake, or record a trace.
- When the user explicitly asks to change, build, fix, or write repository
  artifacts: first run `scripts/bootstrap-harness.sh`
  on macOS/Linux or `.\scripts\bootstrap-harness.ps1` on Windows. Then use
  `docs/FEATURE_INTAKE.md` to classify and record the request, query
  `scripts/bin/harness-cli query matrix --active --summary` on macOS/Linux or
  `.\scripts\bin\harness-cli.exe query matrix --active --summary` on Windows,
  and retrieve only the lane- and task-specific context described in
  `docs/CONTEXT_RULES.md`.
<!-- HARNESS:END -->

## Local Project Notes

- Project: **Hyperagent.com-to-API**. The real product spec has not been
  supplied yet — do not invent product contracts. When the owner provides a
  spec, follow `docs/templates/spec-intake.md` and derive `docs/product/`
  files from it (see `docs/product/SPEC_INTAKE_PENDING.md`).
- Environment: this workspace runs in a Hyperagent sandbox (Amazon Linux
  2023, glibc 2.34, x86_64). The pinned release binary of `harness-cli`
  requires glibc >= 2.39 and does not run here.
- `scripts/bin/harness-cli` is therefore a **locally built** binary compiled
  from upstream source at tag `harness-cli-v0.1.17` (matching
  `scripts/harness-cli-release-tag`). See
  `docs/decisions/0008-locally-built-harness-cli.md`. Do not run the
  installer with `--upgrade-cli` here without rebuilding from source
  afterwards.
- CLI rebuild recipe (when the binary is replaced or the pinned tag changes):
  1. `sudo dnf install -y gcc rust cargo`
  2. Download the pinned-tag source tarball to a directory OUTSIDE this repo
     (a `Cargo.toml` + `crates/harness-cli` at repo root makes bootstrap
     treat this repo as a source checkout and refuse to init state).
  3. `cargo build --release -p harness-cli --locked`
  4. `install -m 755 target/release/harness-cli scripts/bin/harness-cli`
  5. `./scripts/bootstrap-harness.sh`
