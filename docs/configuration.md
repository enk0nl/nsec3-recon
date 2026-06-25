# Configuration Reference

NSEC3 Recon renders scheduler and runtime settings into each run workspace. The checked-in defaults are intended to run the standard AXFR/NSEC/NSEC3 pipeline without editing source files.

## Default namespace scope

The default configuration is tuned for Dutch domains and the `.nl` namespace. It uses Dutch DNS wordlists, OpenTaal Dutch, SecLists DNS data, and PCFG/default generator assets derived from Dutch DNS naming patterns. The pipeline is not limited to `.nl`, but other namespaces should use different candidate sources and scheduler configuration.

## Candidate sources

Scheduler arms can include:

- PCFG-generated DNS label streams. PCFG generation learns DNS-like label patterns from training data and emits candidates that match those patterns.
- Dictionary streams from prepared wordlists.
- Brute-force masks for DNS-like labels.
- Feedback arms derived from recovered names; these generate related candidates from names already cracked or discovered.
- OSINT arms backed by Subfinder and Amass when installed and enabled.

OSINT returns candidate names. Discovered names are AXFR/NSEC/NSEC3-validated outputs.

## Scheduler behavior

The scheduler uses adaptive epsilon-greedy scheduling over configured arms. An arm is one candidate source, such as PCFG, dictionary, brute-force, feedback, or OSINT. A slice is one bounded hashcat run for one candidate source. The scheduler compares the discoveries from each slice and uses that feedback to decide which source to run next. It records per-slice results in `scheduler/jobs.jsonl` and stops early when all target hashes are cracked. It does not guarantee complete name recovery.

Rendered scheduler configuration is written to:

```text
runs/<run>/config/scheduler_config.json
```

## Hashcat settings

NSEC3 hashes are converted into hashcat-compatible mode 8300 input and tested with generated candidate names. Optimized kernels and automatic optimized-kernel failover are enabled by default.

```bash
nsec3-recon example.nl --no-hashcat-optimized-kernels
nsec3-recon example.nl --no-hashcat-optimized-kernel-failover
```

If hashcat reports an optimized-kernel-specific failure and failover is enabled, the scheduler retries the failed slice once with unoptimized kernels and continues unoptimized. Reports record requested and observed optimized-kernel state.

## OSINT settings

Use `--disable-osint` when Amass/Subfinder are unavailable or OSINT traffic is not authorized:

```bash
nsec3-recon example.nl --disable-osint
```

Amass and Subfinder are optional dependencies unless their scheduler arms are enabled.

## Adapting to other namespaces

For non-Dutch namespaces, replace or extend the wordlists, PCFG rules, feedback sources, and scheduler arm weights. Keep generated assets under `assets/` and verify the rendered scheduler config in a dry run before scanning.

```bash
nsec3-recon example.com --dry-run
cat runs/<run>/config/scheduler_config.json
```
