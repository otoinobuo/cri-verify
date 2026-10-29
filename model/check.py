"""Exhaustive comparison: CRI resolution (5.3) + conversion (6.1) versus RFC 3986 resolution of the converted references."""
import sys, itertools, collections
sys.path.insert(0, 'model')
from cri import *
import rfc3986

SEGS = ['a', 'b', '', 'x:y']
import os
MAXP = int(os.environ.get('MAXP', '2')); MAXD = int(os.environ.get('MAXD', '3')); HOSTONLY = os.environ.get('HOSTONLY') == '1'
def paths(maxlen, allow_none):
    out = [None] if allow_none else []
    for L in range(0, maxlen + 1):
        out += [list(p) for p in itertools.product(SEGS, repeat=L)]
    return out

def bases():
    for auth in ([('name', ['h'])] if HOSTONLY else [('name', ['h']), None, True]):
        for p in paths(MAXP, False):
            for q in [[], ['q']]:
                b = cri('s', auth, p, q)
                if not valid_cri(b): continue
                yield b

def refs():
    for d in list(range(0, MAXD + 1)) + [True]:
        for p in paths(MAXP, True):
            for q in [None, [], ['q']]:
                for f in [None, 'f']:
                    yield ref(discard=d, path=p, query=q, fragment=f)
    for sch in [None, 't']:
        for auth in [('name', ['h2']), None, True]:
            if sch is None and auth is not isinstance(auth, tuple) and not isinstance(auth, tuple): continue   # [null, null, ...] must use discard; [null, true, ...] is left unspecified by the draft (see REPORT)
            for p in paths(MAXP, True):
                for q in [None, [], ['q']]:
                    for f in [None, 'f']:
                        r = ref(scheme=sch, authority=auth, path=p, query=q, fragment=f)
                        if sch is not None and (p is None or not valid_cri(cri(sch, auth, p))): continue   # a full CRI used as reference must itself be valid
                        yield r

def size(b, r): return len(show(b)) + len(show(r))

def classify(b, r):
    """Feature string used to group mismatches."""
    ba = 'host' if isinstance(b['authority'], tuple) else ('rootless' if b['authority'] is True else 'rootbased')
    if r['discard'] is None:
        ra = 'host' if isinstance(r['authority'], tuple) else ('true' if r['authority'] is True else 'null')
        rk = 'ref scheme=%s authority=%s' % ('yes' if r['scheme'] else 'no', ra)
    else:
        items = r['path'] if r['path'] is not None else []
        rk = 'discard=%s path=%s' % (r['discard'], 'none' if r['path'] is None else ('empty' if not items else ('lead-empty' if items[0] == '' else 'nonempty')))
        if r['discard'] == 0 and r['query'] is not None and len(r['query']) == 0: rk += ' query=[]'
    return 'base=%s | %s' % (ba, rk)

def run(fixed):
    stats = collections.Counter(); ex = {}
    n = 0; nconv_fail = 0; nres_invalid = 0
    for b in bases():
        ub = to_uri(b)
        for r in refs():
            n += 1
            rr = resolve(b, r, fixed=fixed)
            try: ur_ref = to_uri(r, fixed=fixed)
            except ConversionFails: nconv_fail += 1; continue
            if rr is None: nres_invalid += 1; stats['resolution fails (FIX C\')'] += 1; ex.setdefault('resolution fails (FIX C\')', (b, r, ur_ref, '<fails>', rfc3986.resolve(ub, ur_ref))); continue
            if not valid_cri(rr): nres_invalid += 1; u_cri = '<invalid CRI %s>' % show(rr)
            else: u_cri = to_uri(rr)
            u_uri = rfc3986.resolve(ub, ur_ref)
            if u_cri != u_uri:
                c = classify(b, r); stats[c] += 1
                if c not in ex or size(b, r) < size(*ex[c][:2]): ex[c] = (b, r, ur_ref, u_cri, u_uri)
    print('%s: pairs %d, reference not convertible %d, compared %d, mismatches %d (resolution gave invalid CRI in %d)' %
          ('FIXED' if fixed else 'DRAFT-30', n, nconv_fail, n - nconv_fail, sum(stats.values()), nres_invalid))
    for c, k in sorted(stats.items(), key=lambda x: -x[1]):
        b, r, ur_ref, u_cri, u_uri = ex[c]
        print('  %5d  %s' % (k, c))
        print('         base %s = %s ; ref %s -> URI ref "%s"' % (show(b), to_uri(b), show(r), ur_ref))
        print('         CRI resolution: %s   RFC 3986: %s' % (u_cri, u_uri))
    return stats

if __name__ == '__main__' and '--summary' not in sys.argv:
    run(fixed=False)
    print()
    run(fixed=True)

def summary():
    """Exclusive classification used in Table 1 of the paper (run: python3 model/check.py --summary)."""
    def kind(r):
        if r['discard'] is None: return 'A'
        items = r['path'] if r['path'] is not None else []
        if r['discard'] == 0: return "B'"              # discard 0, no path, query [] (Section 2.3 shape)
        if not items: return 'B'
        if items[0] == '' and r['discard'] == 1: return 'C'
        return 'D'
    nb = {'host': 0, 'noauth': 0}; nr = collections.Counter()
    for b in bases(): nb['host' if isinstance(b['authority'], tuple) else 'noauth'] += 1
    for r in refs(): nr['discard form' if r['discard'] is not None else ('scheme/authority form, scheme absent' if r['scheme'] is None else 'scheme/authority form, scheme present')] += 1
    print('bases:', nb, '| references:', dict(nr), '| total refs', sum(nr.values()))
    for fixed in (False, True):
        cnt = collections.Counter(); comp = collections.Counter()
        for b in bases():
            ba = 'host' if isinstance(b['authority'], tuple) else 'noauth'
            ub = to_uri(b)
            for r in refs():
                try: ur = to_uri(r, fixed=fixed)
                except ConversionFails: continue
                comp[ba] += 1
                rr = resolve(b, r, fixed=fixed)
                if rr is None: cnt[(ba, 'resolution fails')] += 1; continue
                if not valid_cri(rr): cnt[(ba, 'invalid CRI result')] += 1; continue
                if to_uri(rr) != rfc3986.resolve(ub, ur): cnt[(ba, kind(r))] += 1
        print('%s: comparable %s' % ('CORRECTED' if fixed else 'DRAFT-30', dict(comp)))
        for ba in ('host', 'noauth'):
            tot = sum(v for (x, k), v in cnt.items() if x == ba)
            print('   %s: total %d |' % (ba, tot), ' '.join('%s=%d' % (k, cnt[(ba, k)]) for k in ["A", "B", "B'", "C", "D", "invalid CRI result", "resolution fails"] if cnt[(ba, k)]))

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '--summary':
    summary(); sys.exit(0)
