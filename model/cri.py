"""draft-ietf-core-href-30: CRI reference resolution (Section 5.3) and CRI -> URI conversion (Section 6.1).

A CRI reference is a dict with keys scheme, authority, discard, path, query, fragment.
  scheme    : str | None
  authority : None (NOAUTH-ROOTBASED or, with discard present, not set) | True (NOAUTH-ROOTLESS)
              | ('name', [labels]) | ('ip', bytes)
  discard   : int | True | None   (None when scheme/authority form is used)
  path      : list[str] | None
  query     : list[str] | None
  fragment  : str | None
"""
import re

class ConversionFails(Exception): pass

def ref(scheme=None, authority=None, discard=None, path=None, query=None, fragment=None):
    return {'scheme': scheme, 'authority': authority, 'discard': discard, 'path': path, 'query': query, 'fragment': fragment}

def cri(scheme, authority, path, query=(), fragment=None):
    return ref(scheme, authority, None, list(path), list(query), fragment)

def has_sa(r):
    """scheme and/or authority present (Section 5.3 step 3: discard implicitly true)."""
    return r['scheme'] is not None or r['authority'] is not None   # authority True (rootless) counts as present

# ---------------------------------------------------------------- Section 5.3
def resolve(base, r, fixed=False):
    buf = dict(base)                                   # steps 1-2
    buf['path'] = list(base['path']); buf['query'] = list(base['query'])
    d = True if has_sa(r) else r['discard']            # step 3
    if d is True:
        buf['path'] = []; buf['query'] = []; buf['fragment'] = None
        if buf['authority'] is True: buf['authority'] = None
        if fixed and r['scheme'] is not None:          # FIX (A): a reference with a scheme carries its own authority
            buf['authority'] = r['authority']
    else:
        buf['path'] = buf['path'][:max(0, len(buf['path']) - d)]
        if d != 0: buf['query'] = []; buf['fragment'] = None
    if r['path'] is not None:                          # step 4
        buf['path'] = buf['path'] + list(r['path']); buf['query'] = []; buf['fragment'] = None
    if r['query'] is not None: buf['fragment'] = None  # step 5
    for k in ('scheme', 'authority', 'query', 'fragment'):
        if r[k] is not None: buf[k] = r[k] if k != 'query' else list(r[k])
    if fixed and buf['authority'] is True and (not buf['path'] or buf['path'][0] == ''):
        buf['authority'] = None                        # FIX (C): never produce a rootless CRI without a non-empty first segment
    if fixed and buf['authority'] is None and len(buf['path']) >= 2 and buf['path'][0] == '':
        return None                                    # FIX (C'): no valid CRI exists (URI would read as //authority); resolution fails
    buf['discard'] = None
    return buf                                         # step 6

# ---------------------------------------------------------------- Section 6.1
UNRESERVED = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~')
SUBDELIMS = set("!$&'()*+,;=")
def pct(s, extra):
    allowed = UNRESERVED | SUBDELIMS | set(extra)
    return ''.join(c if c in allowed else ''.join('%%%02X' % b for b in c.encode()) for c in s)

PCHAR = r"(?:[A-Za-z0-9\-._~!$&'()*+,;=:@]|%[0-9A-Fa-f]{2})"
PCHAR_NC = r"(?:[A-Za-z0-9\-._~!$&'()*+,;=@]|%[0-9A-Fa-f]{2})"
RE_ABEMPTY  = re.compile(r'^(?:/%s*)*$' % PCHAR)
RE_ABSOLUTE = re.compile(r'^/(?:%s+(?:/%s*)*)?$' % (PCHAR, PCHAR))
RE_NOSCHEME = re.compile(r'^%s+(?:/%s*)*$' % (PCHAR_NC, PCHAR))
RE_ROOTLESS = re.compile(r'^%s+(?:/%s*)*$' % (PCHAR, PCHAR))

def to_uri(r, fixed=False):
    """Return the URI reference string per Section 6.1, or raise ConversionFails."""
    scheme = r['scheme']
    auth = r['authority']
    authority = None
    if isinstance(auth, tuple):
        kind, v = auth
        if kind == 'name':
            if any('.' in l for l in v): raise ConversionFails('dot in label')
            authority = '.'.join(pct(l, '') for l in v)
        else:
            authority = '.'.join(str(b) for b in v) if len(v) == 4 else '[' + ':'.join('%x' % int.from_bytes(v[i:i+2], 'big') for i in range(0, 16, 2)) + ']'
    d = r['discard']
    items = r['path'] if r['path'] is not None else []
    prefix = ''
    if d is True:
        if fixed and len(items) == 0: raise ConversionFails('FIX(B): discard true without path items')
        rooted = True
    elif isinstance(d, int):
        if d == 0:
            if r['path'] is not None: raise ConversionFails('discard 0 with path')
            if fixed and r['query'] is not None and len(r['query']) == 0: raise ConversionFails('FIX(B): discard 0 with empty query')
            rooted = True            # no path items anyway
        else:
            if fixed and len(items) == 0: raise ConversionFails('FIX(B): positive discard without path items')
            rooted = False
            prefix = '../' * (d - 1)
            if d == 1 and items and (':' in items[0] or (fixed and items[0] == '')):
                prefix = './'
    else:                            # scheme/authority form, no discard
        rooted = not (auth is True)
    reps = [pct(it, ':@') for it in items]
    path = prefix + ('' if not reps else ('/' if rooted else '') + '/'.join(reps))
    if authority is not None:
        if not RE_ABEMPTY.match(path): raise ConversionFails('path-abempty')
    elif scheme is not None:
        ok = RE_ABSOLUTE.match(path) or (auth is True and RE_ROOTLESS.match(path)) or path == ''
        if not ok: raise ConversionFails('path with scheme')
    else:
        ok = RE_ABSOLUTE.match(path) or RE_NOSCHEME.match(path) or path == ''
        if not ok: raise ConversionFails('path without scheme/authority')
    query = None
    if r['query']:
        query = '&'.join(pct(q, ':@/?').replace('&', '%26') for q in r['query'])
    fragment = pct(r['fragment'], ':@/?') if r['fragment'] is not None else None
    s = ''
    if scheme is not None: s += scheme + ':'
    if authority is not None: s += '//' + authority
    s += path
    if query is not None: s += '?' + query
    if fragment is not None: s += '#' + fragment
    return s

def show(r):
    """Compact CBOR-like diagnostic notation."""
    def a(x):
        if x is None: return 'null'
        if x is True: return 'true'
        return '[%s]' % ', '.join('"%s"' % l for l in x[1]) if x[0] == 'name' else "h'%s'" % x[1].hex()
    if r['discard'] is not None:
        head = ['true' if r['discard'] is True else str(r['discard'])]
    else:
        head = [('"%s"' % r['scheme']) if r['scheme'] is not None else 'null', a(r['authority'])]
    tail = []
    for k in ('path', 'query'):
        tail.append('null' if r[k] is None else '[%s]' % ', '.join('"%s"' % x for x in r[k]))
    tail.append('null' if r['fragment'] is None else '"%s"' % r['fragment'])
    while tail and tail[-1] in ('null',) : tail.pop()
    return '[' + ', '.join(head + tail) + ']'

def valid_cri(c):
    """Constraints of Section 2 that matter here: C2 (rootless needs a non-empty first segment), C9/2.3 (no leading empty segment followed by more segments when there is no authority)."""
    if c['scheme'] is None: return False
    p = c['path']
    if c['authority'] is True: return len(p) >= 1 and p[0] != ''
    if c['authority'] is None: return not (len(p) >= 2 and p[0] == '')
    return True
