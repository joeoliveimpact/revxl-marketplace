# reel-scripter walk: the two 0.6.0 Goldmine re-walks

From 0.6.0 the Goldmine data is used by default on every reel that has it (`reel-build/goldmine-run.json` shows `reads.passed` true), and the client's only off switch is saying plainly to use their own hook or ignore the data. Two walks prove it: one default-on, one override. Both use the gut fixture with a Goldmine data copy added. Run from the repo root in Git Bash, with the walk token set up as `run-mt2.sh` describes.

## 1. Fresh state folder, reset, then the data

```bash
export RS_WALK_STATE=~/rs-walk-060b            # any NEW folder; never the shared ~/rs-walk-state
mkdir -p "$RS_WALK_STATE" && cp -R ~/rs-walk-state/home ~/rs-walk-state/fixtures "$RS_WALK_STATE/"
bash tests/shortform/reel-scripter-walk/reset.sh gut
# AFTER reset.sh: it rebuilds proj/ from seed-proj/, which has no Goldmine data.
mkdir -p "$RS_WALK_STATE/proj/reel-build"
cp -R "C:/rs-gm-060/Client Brand Project/reel-build/." "$RS_WALK_STATE/proj/reel-build/"   # a Goldmine fixture run's reel-build/
py -3.12 -c "import json,sys; print(json.load(open(sys.argv[1]))['reads']['passed'])" "$RS_WALK_STATE/proj/reel-build/goldmine-run.json"   # must print True
```

The data source is the `reel-build/` of a Goldmine fixture run (the 0.6.0 live test built it at `C:/rs-gm-060/Client Brand Project`; any run whose check-reads passed works). Without the copy, `grade.py --goldmine on|override` FAILS Q and says the file is missing.

## 2. Default-on walk

```bash
bash tests/shortform/reel-scripter-walk/run-mt2.sh 060b-on gut
py -3.12 tests/shortform/reel-scripter-walk/grade.py 060b-on.jsonl --goldmine on
```

Answers: `answers-gut.txt` (the default). Grade it **before** the next reset: the grader reads `proj/scripts/` and `proj/reel-build/goldmine-run.json`.

## 3. Override walk

Repeat step 1's `reset.sh gut` and data copy (same state folder is fine; the logs keep their own names), then:

```bash
RS_WALK_ANSWERS=tests/shortform/reel-scripter-walk/answers-gut-override.txt \
  bash tests/shortform/reel-scripter-walk/run-mt2.sh 060b-override gut
py -3.12 tests/shortform/reel-scripter-walk/grade.py 060b-override.jsonl --goldmine override
```

Answers: `answers-gut-override.txt`, which is `answers-gut.txt` with its OPEN line saying "Use my own hook, ignore the Goldmine data."

## What Q checks

See `RUBRIC.md`, criterion Q: `on` = the data is there and every hook pass used it (Skill args or a read of a Pattern Read / Proven Hooks / reads packet file before its options); `override` = the data is there and nothing in the run passed or opened it; every mode = the old Goldmine question is never asked and the Goldmine is never offered as a question.
