# cri-verify

Machine-checked analysis of CRI reference resolution and conversion (draft-ietf-core-href-30, Sections 5.3 and 6.1)
against RFC 3986 Section 5.2. Companion to the preprint `paper/cri-verify.pdf`.

## Contents
- `paper/` — the preprint (PDF and LaTeX source)
- `lean/Cri.lean` — Lean 4 model, counterexamples (by `decide`) and the soundness theorem `convFixed_sound` for the corrected Section 6.1 conversion; `lean/CrossCheck.lean` — 60 cases computed by the Python model and re-checked by `decide`
- `model/` — Python 3 scripts: `rfc3986.py` (RFC 3986 §5.2, checked against the 42 examples of §5.4), `cri.py` (§5.3 and §6.1 of the draft, with the proposed fixes behind `fixed=True`), `check.py` (exhaustive comparison), `inject.py` (Section 3 objective: distinct CRIs give distinct URIs), `seglevel.py` (segment-level rendering of RFC 3986 that the Lean file formalizes, checked against the string algorithm), and their outputs `*_out.txt`

## Reproduce
```
python3 model/rfc3986.py            # 42 checked, 0 mismatches
python3 model/check.py              # default scale; HOSTONLY=1 MAXP=3 MAXD=4 python3 model/check.py for the larger run
python3 model/inject.py
python3 model/seglevel.py
lean lean/Cri.lean                  # Lean 4.33.1, core only; prints only the #print axioms lines
lean -o /tmp/Cri.olean lean/Cri.lean && LEAN_PATH=/tmp lean lean/CrossCheck.lean
```
All runs finish in seconds except the larger `check.py` run (about two minutes of CPU).

## License
Apache License 2.0 (code and proofs). The paper text is CC BY 4.0.
