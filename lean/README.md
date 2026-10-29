# Cri.lean

Formalization of reference resolution (Section 5.3) and the conversion of CRI references to URI references (Section 6.1)
of draft-ietf-core-href-30 (Constrained Resource Identifiers), compared with RFC 3986 Sections 5.2.2-5.2.4 (merge and
remove_dot_segments) at the level of lists of path segments.

- Check: `lean Cri.lean` with Lean 4.33.1 (about 2 seconds). The only output is the `#print axioms` lines; neither
  `sorryAx` nor `Classical.choice` appears.
- Counterexamples (by `decide`): `cex_discard_without_path` ([1] becomes ""), `cex_leading_empty_segment`
  ([1, ["", "a"]] becomes "/a"), `cex_discard_two_without_path` ([2, []] becomes "../"), `cex_discard_zero_empty_query`
  ([0, null, []] becomes ""), `cex_null_authority` (step 5 does not copy a null authority).
- Theorem `convFixed_sound`: for every base with an authority and every path without dot segments (C9), resolving the
  URI reference produced by the corrected Section 6.1 conversion per RFC 3986 gives the same result as the Section 5.3
  CRI resolution.
- `CrossCheck.lean`: 60 cases computed by the Python model (../model) re-checked by `decide`
  (`lean -o <dir>/Cri.olean Cri.lean`, then `LEAN_PATH=<dir> lean CrossCheck.lean`).
- Out of scope: bases without an authority (the Python enumeration shows differences from RFC 3986 there; the paper
  makes no claim about them), conversion of host names, IP addresses, ports and userinfo, and percent-encoding.
