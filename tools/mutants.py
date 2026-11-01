"""Run every test's mutants: each must fail with a FAIL line. A mutant whose text isn't in the
code exactly once also exits non-zero, so that case is reported apart, never as caught.

    python mutants.py            every test_*.py here
    python mutants.py census     only test_census.py
"""
import ast
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def mutant_names(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "MUTANTS" for t in node.targets):
            return [k.value for k in node.value.keys]
    return []


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    tests = sorted(glob.glob(os.path.join(HERE, "test_*.py")))
    if only:
        tests = [t for t in tests if os.path.basename(t) == "test_%s.py" % only]
    caught, bad = 0, []
    for t in tests:
        base = subprocess.run([sys.executable, "-I", t], capture_output=True, text=True)
        if base.returncode != 0:
            bad.append("%s fails without a mutant:\n%s" % (os.path.basename(t), base.stdout + base.stderr))
            continue
        for name in mutant_names(t):
            r = subprocess.run([sys.executable, "-I", t, name], capture_output=True, text=True)
            label = "%s %s" % (os.path.basename(t), name)
            if r.returncode == 3:
                bad.append(label + ": its text isn't in the code exactly once")
            elif r.returncode == 0:
                bad.append(label + ": NOT caught")
            elif "FAIL" not in r.stdout:
                bad.append(label + ": failed without a FAIL line:\n" + (r.stdout + r.stderr)[-400:])
            else:
                caught += 1
    for b in bad:
        print(b)
    print("%d mutants caught, %d problems" % (caught, len(bad)))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
