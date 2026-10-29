# model/

- `rfc3986.py`: RFC 3986 Section 5.2 reference resolution on strings. `python3 rfc3986.py` self-checks the 42 examples of Section 5.4.
- `cri.py`: Sections 5.3 (resolve) and 6.1 (to_uri) of draft-ietf-core-href-30. `fixed=True` enables the proposed corrections.
- `check.py`: enumerates bases (scheme s; authority = host / null / true; paths of up to 2 segments; query) against CRI
  references (discard 0-3 and true; scheme and authority forms), and compares the URI of the CRI resolution with the
  RFC 3986 resolution of the converted URI reference. Output: `check_out.txt`.
- `inject.py`: checks the Section 3 objective (distinct CRIs do not give the same URI) on a small set of components. Output: `inject_out.txt`.
- `seglevel.py`: checks that the segment-level rendering of RFC 3986 (the one formalized in Lean) agrees with the string algorithm. Output: `seglevel_out.txt`.

Every script finishes in seconds.
