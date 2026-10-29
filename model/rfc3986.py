"""RFC 3986 (STD 66) Section 5.2 reference resolution, implemented literally on strings."""
import re
_RE = re.compile(r'^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?$')

def parse(s):
    m = _RE.match(s)
    return {'scheme': m.group(2), 'authority': m.group(4), 'path': m.group(5),
            'query': m.group(7), 'fragment': m.group(9)}

def recompose(c):                       # Section 5.3
    r = ''
    if c['scheme'] is not None: r += c['scheme'] + ':'
    if c['authority'] is not None: r += '//' + c['authority']
    r += c['path']
    if c['query'] is not None: r += '?' + c['query']
    if c['fragment'] is not None: r += '#' + c['fragment']
    return r

def merge(base, rpath):                 # Section 5.2.3
    if base['authority'] is not None and base['path'] == '':
        return '/' + rpath
    p = base['path']
    i = p.rfind('/')
    return (p[:i+1] if i >= 0 else '') + rpath

def remove_dot_segments(inp):           # Section 5.2.4
    out = ''
    while inp:
        if inp.startswith('../'): inp = inp[3:]
        elif inp.startswith('./'): inp = inp[2:]
        elif inp.startswith('/./'): inp = inp[2:]
        elif inp == '/.': inp = '/'
        elif inp.startswith('/../'):
            inp = inp[3:]; out = out[:out.rfind('/')] if '/' in out else ''
        elif inp == '/..':
            inp = '/'; out = out[:out.rfind('/')] if '/' in out else ''
        elif inp in ('.', '..'): inp = ''
        else:
            start = 1 if inp.startswith('/') else 0
            j = inp.find('/', start)
            if j < 0: j = len(inp)
            out += inp[:j]; inp = inp[j:]
    return out

def resolve(base, ref):                 # Section 5.2.2 (strict)
    B = parse(base) if isinstance(base, str) else base
    R = parse(ref) if isinstance(ref, str) else ref
    T = {}
    if R['scheme'] is not None:
        T['scheme'] = R['scheme']; T['authority'] = R['authority']
        T['path'] = remove_dot_segments(R['path']); T['query'] = R['query']
    else:
        if R['authority'] is not None:
            T['authority'] = R['authority']; T['path'] = remove_dot_segments(R['path']); T['query'] = R['query']
        else:
            if R['path'] == '':
                T['path'] = B['path']
                T['query'] = R['query'] if R['query'] is not None else B['query']
            else:
                if R['path'].startswith('/'): T['path'] = remove_dot_segments(R['path'])
                else: T['path'] = remove_dot_segments(merge(B, R['path']))
                T['query'] = R['query']
            T['authority'] = B['authority']
        T['scheme'] = B['scheme']
    T['fragment'] = R['fragment']
    return recompose(T)

# Section 5.4 examples (normal + abnormal), used as a self-test of this implementation.
BASE = 'http://a/b/c/d;p?q'
EXAMPLES = {
 'g:h':'g:h','g':'http://a/b/c/g','./g':'http://a/b/c/g','g/':'http://a/b/c/g/','/g':'http://a/g','//g':'http://g',
 '?y':'http://a/b/c/d;p?y','g?y':'http://a/b/c/g?y','#s':'http://a/b/c/d;p?q#s','g#s':'http://a/b/c/g#s',
 'g?y#s':'http://a/b/c/g?y#s',';x':'http://a/b/c/;x','g;x':'http://a/b/c/g;x','g;x?y#s':'http://a/b/c/g;x?y#s',
 '':'http://a/b/c/d;p?q','.':'http://a/b/c/','./':'http://a/b/c/','..':'http://a/b/','../':'http://a/b/',
 '../g':'http://a/b/g','../..':'http://a/','../../':'http://a/','../../g':'http://a/g',
 '../../../g':'http://a/g','../../../../g':'http://a/g','/./g':'http://a/g','/../g':'http://a/g','g.':'http://a/b/c/g.',
 '.g':'http://a/b/c/.g','g..':'http://a/b/c/g..','..g':'http://a/b/c/..g','./../g':'http://a/b/g','./g/.':'http://a/b/c/g/',
 'g/./h':'http://a/b/c/g/h','g/../h':'http://a/b/c/h','g;x=1/./y':'http://a/b/c/g;x=1/y','g;x=1/../y':'http://a/b/c/y',
 'g?y/./x':'http://a/b/c/g?y/./x','g?y/../x':'http://a/b/c/g?y/../x','g#s/./x':'http://a/b/c/g#s/./x','g#s/../x':'http://a/b/c/g#s/../x',
 'http:g':'http:g',
}
if __name__ == '__main__':
    bad = [(r, resolve(BASE, r), e) for r, e in EXAMPLES.items() if resolve(BASE, r) != e]
    print('RFC 3986 section 5.4 examples:', len(EXAMPLES), 'checked,', len(bad), 'mismatches', bad)
