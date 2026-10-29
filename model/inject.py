"""Section 3 objective: two distinct (normalized, valid) CRIs must not convert to the same URI (modulo syntax-based normalization)."""
import sys, itertools, collections
sys.path.insert(0, 'model')
from cri import *

def norm(u):   # RFC 3986 6.2.2: case of scheme/host lowered (our outputs already are), percent-encoding of unreserved decoded (never produced)
    return u

LABELS = ['h', '1', '2', '', 'a-b']
auths = [None, True, ('ip', bytes([1,2,1,2])), ('ip', bytes([10,0,0,1]))]
for L in range(1, 5):
    for labs in itertools.product(LABELS, repeat=L):
        auths.append(('name', list(labs)))
SEGS = ['a', '', 'x:y', 'a/b', 'a&b', '%41', 'A']
QS = ['q', '', 'a&b', 'a=b', '%26']
seen = collections.defaultdict(list); n = 0
for auth in auths:
    for L in range(0, 3):
        for p in itertools.product(SEGS, repeat=L):
            for q in [[], [''], ['q'], ['a&b'], ['a', 'b'], ['%26']]:
                for f in [None, '', 'f']:
                    c = cri('s', auth, list(p), q, f)
                    if not valid_cri(c): continue
                    try: u = to_uri(c)
                    except ConversionFails: continue
                    n += 1; seen[norm(u)].append(show(c))
coll = {u: v for u, v in seen.items() if len(v) > 1}
print('valid convertible CRIs:', n, '; distinct URIs:', len(seen), '; URIs with >1 CRI:', len(coll))
for u, v in sorted(coll.items(), key=lambda x: len(x[0]))[:8]:
    print('  ', u, '<=', ' | '.join(v))
