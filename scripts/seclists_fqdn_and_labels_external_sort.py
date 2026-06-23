#!/usr/bin/env python3
from __future__ import annotations
import argparse
import subprocess
import tempfile
from pathlib import Path


def normalize_line(line: str, keep_case: bool, keep_trailing_dot: bool) -> str | None:
    value = line.strip()
    if not keep_trailing_dot and value.endswith("."):
        value = value[:-1]
    if not keep_case:
        value = value.lower()
    return value or None


def emit_candidates(value: str, double_count_single_labels: bool) -> list[str]:
    labels = [part for part in value.split(".") if part]
    if double_count_single_labels:
        return [value, *labels]
    candidates = {value}
    candidates.update(labels)
    return sorted(candidates)


def input_files(input_dir: Path, recursive: bool, extra_inputs: list[Path], out_prefix: Path) -> list[Path]:
    pattern = "**/*.txt" if recursive else "*.txt"
    output_paths = {out_prefix.with_name(out_prefix.name + suffix).resolve() for suffix in ("_total.txt", "_total_counts.tsv")}
    files: list[Path] = []
    for path in input_dir.glob(pattern):
        if not path.is_file():
            continue
        if path.suffix != ".txt" or path.resolve() in output_paths or path.name.endswith("_counts.tsv"):
            continue
        files.append(path)
    files.extend(extra_inputs)
    return files


def stream_candidates(files: list[Path], candidates_path: Path, keep_case: bool, keep_trailing_dot: bool, double_count_single_labels: bool) -> None:
    with candidates_path.open("w", encoding="utf-8") as out:
        for path in files:
            with path.open("r", encoding="utf-8", errors="ignore") as src:
                for line in src:
                    value = normalize_line(line, keep_case, keep_trailing_dot)
                    if not value:
                        continue
                    for candidate in emit_candidates(value, double_count_single_labels):
                        if candidate:
                            out.write(candidate + "\n")


def run_sort_count(candidates_path: Path, out_prefix: Path, sort_memory: str, tmp_dir: Path, min_count: int, leading_empty_line: bool, keep_counts: bool) -> tuple[Path | None, Path]:
    sorted_path = candidates_path.with_suffix(".sorted")
    unsorted_counts = candidates_path.with_suffix(".counts.tsv")
    output_counts_path = out_prefix.with_name(out_prefix.name + "_total_counts.tsv")
    counts_path = candidates_path.with_suffix(".final_counts.tsv")
    values_path = out_prefix.with_name(out_prefix.name + "_total.txt")
    with sorted_path.open("w", encoding="utf-8") as sorted_out:
        subprocess.run(["sort", "-S", sort_memory, "-T", str(tmp_dir), str(candidates_path)], check=True, stdout=sorted_out)
    raw_counts_path = candidates_path.with_suffix(".uniq_counts.txt")
    with raw_counts_path.open("w", encoding="utf-8") as raw_counts:
        subprocess.run(["uniq", "-c", str(sorted_path)], check=True, text=True, stdout=raw_counts)
    with raw_counts_path.open("r", encoding="utf-8") as counts_in, unsorted_counts.open("w", encoding="utf-8") as out:
        for line in counts_in:
            stripped = line.strip()
            if not stripped:
                continue
            count, candidate = stripped.split(maxsplit=1)
            if int(count) >= min_count:
                out.write(f"{count}\t{candidate}\n")
    with counts_path.open("w", encoding="utf-8") as out:
        subprocess.run(["sort", "-S", sort_memory, "-T", str(tmp_dir), "-t", "\t", "-k1,1nr", "-k2,2", str(unsorted_counts)], check=True, stdout=out)
    with counts_path.open("r", encoding="utf-8") as src, values_path.open("w", encoding="utf-8") as out:
        if leading_empty_line:
            out.write("\n")
        for line in src:
            parts = line.rstrip("\n").split("\t", 1)
            if len(parts) == 2:
                out.write(parts[1] + "\n")
    if keep_counts:
        output_counts_path.parent.mkdir(parents=True, exist_ok=True)
        output_counts_path.write_text(counts_path.read_text(encoding="utf-8"), encoding="utf-8")
        return output_counts_path, values_path
    return None, values_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Combine SecLists DNS FQDNs and labels using GNU sort/uniq")
    parser.add_argument("--input-dir", "-i", required=True, type=Path)
    parser.add_argument("--out-prefix", "-o", required=True, type=Path)
    parser.add_argument("--extra-input", action="append", default=[], type=Path)
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--min-count", type=int, default=1)
    parser.add_argument("--keep-case", action="store_true")
    parser.add_argument("--keep-trailing-dot", action="store_true")
    parser.add_argument("--double-count-single-labels", action="store_true")
    parser.add_argument("--sort-memory", default="1G")
    parser.add_argument("--keep-counts", action="store_true")
    parser.add_argument("--tmp-dir", type=Path, default=Path(tempfile.gettempdir()))
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--leading-empty-line", dest="leading_empty_line", action="store_true", default=True)
    group.add_argument("--no-leading-empty-line", dest="leading_empty_line", action="store_false")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    args.out_prefix.parent.mkdir(parents=True, exist_ok=True)
    args.tmp_dir.mkdir(parents=True, exist_ok=True)
    files = input_files(args.input_dir, args.recursive, args.extra_input, args.out_prefix)
    with tempfile.TemporaryDirectory(dir=args.tmp_dir) as tmp:
        candidates_path = Path(tmp) / "candidates.txt"
        stream_candidates(files, candidates_path, args.keep_case, args.keep_trailing_dot, args.double_count_single_labels)
        run_sort_count(candidates_path, args.out_prefix, args.sort_memory, Path(tmp), args.min_count, args.leading_empty_line, args.keep_counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
