"""Segment-level rendering of RFC 3986 5.2.2-5.2.4 for bases WITH an authority (rooted paths).
This is the model that lean/Cri.lean formalizes; `python3 model/seglevel.py` checks it against the literal string
algorithm (rfc3986.py).  `uref_of` renders the Section 6.1 conversion (draft text or corrected) in segment form."""
import sys, os, itertools
sys.path.insert(0, os.path.dirname(__file__))
import rfc3986
from cri import *
import check

def rds_segs(segs):
    """remove_dot_segments on a rooted path given as segment list; returns segment list (rooted)."""
    out = []
    n = len(segs)
    for i, s in enumerate(segs):
        last = (i == n - 1)
        if s == '.':
            if last: out.append('')
        elif s == '..':
            if out: out.pop()
            if last: out.append('')
        else:
            out.append(s)
    return out

def merge_segs(base_segs, ref_segs):
    """5.2.3 for a base with authority: empty base path -> '/' + ref ; else drop the last base segment."""
    return list(ref_segs) if not base_segs else base_segs[:-1] + list(ref_segs)

def path_str(rooted, segs):
    if not segs: return ''
    return ('/' if rooted else '') + '/'.join(segs)

def resolve_segs(base, uref):
    """uref = dict(rooted: bool, segs: list|None (None = empty path ''), query: list|None, fragment)
    base = full CRI with host authority. Returns (path segs, query, fragment) of the target per 5.2.2."""
    if uref['segs'] is None:                       # R.path == ""
        return list(base['path']), (uref['query'] if uref['query'] is not None else list(base['query'])), uref['fragment']
    if uref['rooted']: tp = rds_segs(uref['segs'])
    else: tp = rds_segs(merge_segs(base['path'], uref['segs']))
    return tp, uref['query'], uref['fragment']

def uref_of(r, fixed):
    """The URI reference produced by Section 6.1 (as in cri.to_uri) in segment form."""
    d = r['discard']; items = r['path'] if r['path'] is not None else []
    if d is True:
        if fixed and not items: raise ConversionFails
        segs = list(items) if items else None; rooted = True
    elif d == 0:
        if r['path'] is not None: raise ConversionFails
        if fixed and r['query'] is not None and len(r['query']) == 0: raise ConversionFails
        segs = None; rooted = False
    else:
        if fixed and not items: raise ConversionFails
        rooted = False
        if d == 1:
            segs = (['.'] + items) if items and (':' in items[0] or (fixed and items[0] == '')) else list(items)
        else:
            segs = ['..'] * (d - 1) + list(items)
        if not segs: segs = None
        elif not fixed and segs[0] == '':          # string collapse of the draft conversion: "" + "/a" renders as "/a", "" alone as ""
            if len(segs) == 1: segs = None
            else: rooted = True; segs = segs[1:]
    return {'rooted': rooted, 'segs': segs, 'query': (list(r['query']) if r['query'] else None), 'fragment': r['fragment']}

if __name__ == '__main__':
    # --- check 1: rds_segs vs string remove_dot_segments on rooted paths of one to five segments
    SEG = ['a', '', '.', '..']
    bad = 0; n = 0
    for L in range(1, 6):
        for segs in itertools.product(SEG, repeat=L):
            s = '/' + '/'.join(segs)
            got = rds_segs(list(segs)); want = rfc3986.remove_dot_segments(s)
            n += 1
            if path_str(True, got) != want and not (got == [] and want == ''):
                bad += 1
                if bad < 5: print('rds mismatch', s, got, want)
    print('check 1: rooted paths', n, 'mismatches', bad)
    # --- check 2: segment-level resolution vs string resolution for host bases and discard-form references (both conversions)
    for fixed in (False, True):
        n = 0; bad = 0; skipped = 0
        for b in check.bases():
            if not isinstance(b['authority'], tuple): continue
            ub = to_uri(b)
            for r in check.refs():
                if r['discard'] is None: continue
                try: ur_str = to_uri(r, fixed=fixed); u = uref_of(r, fixed)
                except ConversionFails: skipped += 1; continue
                n += 1
                tp, tq, tf = resolve_segs(b, u)
                want = rfc3986.resolve(ub, ur_str)
                got = to_uri(cri(b['scheme'], b['authority'], tp, tq if tq is not None else [], tf))
                if got != want:
                    bad += 1
                    if bad < 4: print('resolve mismatch', show(b), show(r), ur_str, got, want)
        print('check 2 (%s): host bases x discard refs: %d compared, %d skipped (not convertible), mismatches %d' % ('fixed' if fixed else 'draft', n, skipped, bad))
