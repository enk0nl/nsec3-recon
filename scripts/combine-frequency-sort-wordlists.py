#!/usr/bin/env python3
from __future__ import annotations
import argparse
import importlib.util
import shutil
import tempfile
from pathlib import Path

_IMPL = Path(__file__).with_name("seclists_fqdn_and_labels_external_sort.py")
spec = importlib.util.spec_from_file_location("seclists_external_sort", _IMPL)
impl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impl)  # type: ignore[union-attr]


def combine(inputs):
    with tempfile.TemporaryDirectory() as tmp:
        out_prefix = Path(tmp) / "combined"
        impl.main(["--input-dir", tmp, "--out-prefix", str(out_prefix), "--no-leading-empty-line", *sum((["--extra-input", str(p)] for p in inputs), [])])
        return (out_prefix.with_name(out_prefix.name + "_total.txt")).read_text().splitlines()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("inputs", nargs="+")
    args = parser.parse_args(argv)
    output = Path(args.output)
    with tempfile.TemporaryDirectory() as tmp:
        out_prefix = Path(tmp) / "combined"
        cli = ["--input-dir", tmp, "--out-prefix", str(out_prefix), "--no-leading-empty-line"]
        for item in args.inputs:
            cli.extend(["--extra-input", item])
        impl.main(cli)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out_prefix.with_name(out_prefix.name + "_total.txt"), output)


if __name__ == "__main__":
    main()
