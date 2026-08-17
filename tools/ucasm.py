#!/usr/bin/env python3
"""Compilatore del microcodice di EVSCPU.

    ucasm.py ucode/evscpu.uc -o ucode
    ucasm.py ucode/evscpu.uc -patch EVSCPU.CircuitProject
    ucasm.py ucode/evscpu.uc -report
"""

import argparse
import base64
import re
import sys


class Error(Exception):
    def __init__(self, line, msg):
        super().__init__('riga %d: %s' % (line, msg))


class Cursor:
    TOKEN = re.compile(r'[{}|:=;()@]|[^\s{}|:=;()@]+')

    def __init__(self, text):
        self.toks = []
        for n, raw in enumerate(text.splitlines(), 1):
            for m in self.TOKEN.finditer(re.sub(r'#.*', '', raw)):
                self.toks.append((m.group(0), n))
        self.pos = 0

    def eof(self):
        return self.pos >= len(self.toks)

    def peek(self):
        return self.toks[self.pos][0] if not self.eof() else None

    def line(self):
        return self.toks[min(self.pos, len(self.toks) - 1)][1] if self.toks else 0

    def next(self):
        if self.eof():
            raise Error(self.line(), 'fine del sorgente inattesa')
        t, _ = self.toks[self.pos]
        self.pos += 1
        return t

    def want(self, tok):
        line = self.line()
        got = self.next()
        if got != tok:
            raise Error(line, 'atteso %r, trovato %r' % (tok, got))

    def accept(self, tok):
        if self.peek() == tok:
            self.pos += 1
            return True
        return False


def number(tok, line):
    try:
        return int(tok, 0)
    except ValueError:
        raise Error(line, '%r non e\' un numero' % tok)


class Signal:
    def __init__(self, name, hi, lo):
        self.name, self.hi, self.lo = name, hi, lo
        self.mask = ((1 << (hi - lo + 1)) - 1) << lo

    @property
    def width(self):
        return (1 << (self.hi - self.lo + 1)) - 1

    def encode(self, value, line):
        top = (1 << (self.hi - self.lo + 1)) - 1
        if not 0 <= value <= top:
            raise Error(line, '%d non sta in %s' % (value, self.name))
        return value << self.lo

    def span(self):
        return str(self.hi) if self.hi == self.lo else '%d:%d' % (self.hi, self.lo)


class Value:
    def __init__(self, name, word, mask, param, line):
        self.name, self.word, self.mask = name, word, mask
        self.param, self.line = param, line


class Field:
    def __init__(self, name, line):
        self.name, self.line, self.values = name, line, {}

    @property
    def default(self):
        return next(iter(self.values.values()))

    @property
    def mask(self):
        m = 0
        for v in self.values.values():
            m |= v.mask
        return m


class Word:
    def __init__(self, line):
        self.line, self.chosen, self.branch = line, {}, None
        self.addr = None

    def copy(self):
        w = Word(self.line)
        w.chosen, w.branch = dict(self.chosen), self.branch
        return w


class Routine:
    def __init__(self, name, line):
        self.name, self.line = name, line
        self.words, self.labels = [], {}
        self.start = None


class Program:
    def __init__(self):
        self.width, self.rom, self.slot, self.entry = 24, 128, 8, 4
        self.signals, self.fields = {}, {}
        self.routines, self.placed, self.opcodes = {}, [], {}


def parse(text):
    p = Program()
    c = Cursor(text)

    def terms(stop):
        word = mask = 0
        while c.peek() not in stop:
            line = c.line()
            name = c.next()
            if name not in p.signals:
                raise Error(line, 'segnale %r non dichiarato' % name)
            sig = p.signals[name]
            value = number(c.next(), line) if c.accept('=') else \
                (1 << (sig.hi - sig.lo + 1)) - 1
            if mask & sig.mask:
                raise Error(line, '%s assegnato due volte' % name)
            word |= sig.encode(value, line)
            mask |= sig.mask
        return word, mask

    while not c.eof():
        line = c.line()
        kw = c.next()
        if kw in ('width', 'rom', 'slot', 'entry'):
            setattr(p, kw, number(c.next(), line))
        elif kw == 'signal':
            name, spec = c.next(), c.next()
            hi, lo = (number(spec, line), number(c.next(), line)) if c.accept(':') \
                else (number(spec, line),) * 2
            if lo > hi:
                hi, lo = lo, hi
            sig = Signal(name, hi, lo)
            if name in p.signals:
                raise Error(line, 'segnale %r gia\' dichiarato' % name)
            if hi >= p.width:
                raise Error(line, '%s esce dalla control word' % name)
            for o in p.signals.values():
                if o.mask & sig.mask:
                    raise Error(line, '%s si sovrappone a %s' % (name, o.name))
            p.signals[name] = sig
        elif kw == 'field':
            name = c.next()
            if name in p.fields:
                raise Error(line, 'campo %r gia\' dichiarato' % name)
            f = Field(name, line)
            c.want('{')
            while True:
                vline = c.line()
                vname = c.next()
                param = None
                if c.accept('('):
                    param = c.next()
                    c.want(')')
                    if param not in p.signals:
                        raise Error(vline, 'parametro %r non e\' un segnale' % param)
                word, mask = terms(('|', '}')) if c.accept(':') else (0, 0)
                if vname in f.values:
                    raise Error(vline, 'valore %r ripetuto' % vname)
                f.values[vname] = Value(vname, word, mask, param, vline)
                if c.accept('}'):
                    break
                c.want('|')
            p.fields[name] = f
        elif kw == 'routine':
            name = c.next()
            if name in p.routines:
                raise Error(line, 'routine %r gia\' definita' % name)
            r = Routine(name, line)
            c.want('{')
            while not c.accept('}'):
                w = Word(c.line())
                while not c.accept(';'):
                    wline = c.line()
                    tok = c.next()
                    if c.accept(':'):
                        if tok in r.labels:
                            raise Error(wline, 'etichetta %r ripetuta' % tok)
                        r.labels[tok] = len(r.words)
                        continue
                    if tok not in p.fields:
                        raise Error(wline, 'campo %r non dichiarato' % tok)
                    if tok in w.chosen:
                        raise Error(wline, 'campo %r assegnato due volte' % tok)
                    c.want('=')
                    vline = c.line()
                    vname = c.next()
                    field = p.fields[tok]
                    if vname not in field.values:
                        raise Error(vline, '%s non ha il valore %r' % (tok, vname))
                    value = field.values[vname]
                    arg = None
                    if c.accept('('):
                        arg = (c.next(), c.line())
                        c.want(')')
                    if bool(arg) != bool(value.param):
                        raise Error(vline, '%s=%s vuole %s argomento'
                                    % (tok, vname, 'un' if value.param else 'nessun'))
                    if arg:
                        w.branch = (value.param, arg[0], arg[1])
                    w.chosen[tok] = value
                r.words.append(w)
            p.routines[name] = r
        elif kw == 'at':
            addr = number(c.next(), line)
            p.placed.append((addr, c.next(), line))
        elif kw == 'opcode':
            code = number(c.next(), line)
            mnemonic = c.next()
            c.want('=')
            p.opcodes[code] = (mnemonic, c.next(), line)
        else:
            raise Error(line, 'direttiva %r sconosciuta' % kw)
    return p


def layout(p):
    """Assegna un indirizzo a ogni parola e verifica che nessuna si sovrapponga."""
    owner = [None] * p.rom
    for addr, name, line in p.placed:
        if name not in p.routines:
            raise Error(line, 'routine %r inesistente' % name)
        p.routines[name].start = (addr, line)
    for code in sorted(p.opcodes):
        mnemonic, name, line = p.opcodes[code]
        if name not in p.routines:
            raise Error(line, 'routine %r inesistente' % name)
        if code * p.slot >= p.rom:
            raise Error(line, 'opcode %#x fuori dalla ROM' % code)
        r = p.routines[name]
        start = code * p.slot + p.entry
        if r.start is None or r.start[0] == start:
            r.start = (start, line)
        else:
            # una routine condivisa da piu' opcode viene replicata in ogni slot
            clone = Routine(name, r.line)
            clone.words = [w.copy() for w in r.words]
            clone.labels = dict(r.labels)
            clone.start = (start, line)
            p.routines['%s@%#x' % (name, code)] = clone
    for name, r in list(p.routines.items()):
        if r.start is None:
            raise Error(r.line, 'routine %r non collocata' % name)
        for i, w in enumerate(r.words):
            addr = r.start[0] + i
            if addr >= p.rom:
                raise Error(w.line, '%s esce dalla ROM' % name)
            if owner[addr] is not None:
                raise Error(w.line, '%s: collisione a %#04x con %s'
                            % (name, addr, owner[addr]))
            owner[addr] = name
            w.addr = addr
    return owner


def encode(p):
    """Risolve i riferimenti e costruisce la parola di controllo di ogni stato."""
    for r in p.routines.values():
        for i, w in enumerate(r.words):
            word = used = 0
            for f in p.fields.values():
                value = w.chosen.get(f.name, f.default)
                if used & value.mask:
                    raise Error(w.line, 'due campi scrivono gli stessi bit')
                word |= value.word
                used |= value.mask
            if w.branch:
                signal, arg, line = w.branch
                if arg in r.labels:
                    target = r.start[0] + r.labels[arg]
                    if target // p.slot != w.addr // p.slot:
                        raise Error(line, '%s: il bersaglio %r e\' in un altro slot'
                                    % (r.name, arg))
                    target %= p.slot
                else:
                    target = number(arg, line)
                    if not 0 <= target < p.slot:
                        raise Error(line, '%s: la parola %d e\' fuori dallo slot'
                                    % (r.name, target))
                word |= p.signals[signal].encode(target, line)
            w.word = word
    rom = [0] * p.rom
    for r in p.routines.values():
        for w in r.words:
            rom[w.addr] = w.word
    return rom


def sequencer(p):
    """Semantica del campo che scegle il prossimo uPC, ricavata dal listato."""
    field = p.fields.get('next')
    if field is None:
        raise Error(0, "manca il campo 'next': il sequencer non e' descritto")
    kinds = {}
    for v in field.values.values():
        kinds[v.name] = v.name if v.name in ('dispatch', 'goto', 'brz') else 'step'
    return field, kinds


def check(p, rom, owner):
    errors, warnings = [], []
    field, kinds = sequencer(p)

    for a in p.fields.values():
        for b in p.fields.values():
            if a is not b and a.mask & b.mask:
                errors.append('i campi %s e %s condividono dei bit' % (a.name, b.name))

    def kind(w):
        return kinds[w.chosen.get('next', field.default).name]

    for r in p.routines.values():
        index = {w.addr: w for w in r.words}

        def walk(w, taken, seen, fetched):
            """Percorre un cammino fino al dispatch, seguendo o no il salto."""
            while True:
                if w.addr in seen:
                    errors.append('riga %d: %s: microloop' % (w.line, r.name))
                    return
                seen = seen | {w.addr}
                does_fetch = w.chosen.get('mem') and w.chosen['mem'].name == 'fetch'
                k = kind(w)
                if k == 'dispatch':
                    value = w.chosen.get('next', field.default)
                    wants_ir = value is not field.default and \
                        not does_fetch and value.name.endswith('_ir')
                    if not does_fetch and not wants_ir:
                        errors.append('riga %d: %s dispatcha senza fetch: '
                                      'l\'opcode non e\' quello nuovo' % (w.line, r.name))
                    if wants_ir and not fetched:
                        errors.append('riga %d: %s dispatcha da IR senza aver mai '
                                      'fatto fetch' % (w.line, r.name))
                    return
                nxt = None
                if k in ('goto', 'brz') and (k == 'goto' or taken):
                    target = rom[w.addr] >> p.signals[w.branch[0]].lo & p.signals[w.branch[0]].width
                    nxt = index.get(w.addr - w.addr % p.slot + target)
                if nxt is None:
                    nxt = index.get(w.addr + 1)
                if nxt is None:
                    errors.append('riga %d: %s continua fuori dalle proprie parole'
                                  % (w.line, r.name))
                    return
                w, fetched = nxt, fetched or does_fetch

        for taken in (False, True):
            walk(r.words[0], taken, frozenset(), False)

        for w in r.words:
            mem = w.chosen.get('mem')
            if mem and mem.name == 'write' and w.chosen.get('tr'):
                errors.append('riga %d: %s scrive in memoria e carica TR: il dato '
                              'scritto cambierebbe durante la scrittura'
                              % (w.line, r.name))
            if w.chosen.get('ar') and w.chosen['ar'].name == 'load' \
                    and not w.chosen.get('bus_a'):
                errors.append('riga %d: %s carica AR senza master sul bus A'
                              % (w.line, r.name))
            if rom[w.addr] & ~sum(s.mask for s in p.signals.values()):
                errors.append('riga %d: %s accende bit non dichiarati' % (w.line, r.name))

    for code in range(p.rom // p.slot):
        if code not in p.opcodes:
            warnings.append('opcode %#x senza routine: cade nel riempimento' % code)
    covered = 0
    for s in p.signals.values():
        covered |= s.mask
    free = [b for b in range(p.width) if not covered >> b & 1]
    return errors, warnings, free


def cycles(p, code):
    """Cicli per macroistruzione: dal dispatch fino al dispatch successivo."""
    field, kinds = sequencer(p)
    rom = {w.addr: w for r in p.routines.values() for w in r.words}
    out = []
    for taken in (False, True):
        addr, n = code * p.slot + p.entry, 0
        while n <= p.slot * 2:
            w = rom.get(addr)
            if w is None:
                return None
            n += 1
            k = kinds[w.chosen.get('next', field.default).name]
            if k == 'dispatch':
                break
            if k == 'goto' or (k == 'brz' and taken):
                addr = addr - addr % p.slot + (rom[addr].word >> p.signals[w.branch[0]].lo & p.signals[w.branch[0]].width)
            else:
                addr += 1
        out.append(n)
    return out


def listing(p, rom, owner):
    field = p.fields['next']
    index = {w.addr: (r, i) for r in p.routines.values() for i, w in enumerate(r.words)}
    out = ['; generato da tools/ucasm.py', '',
           '; control word (%d bit)' % p.width]
    for s in sorted(p.signals.values(), key=lambda s: -s.hi):
        out.append(';   %5s  %s' % (s.span(), s.name))
    out += ['', '; microcodice']
    for addr in range(p.rom):
        if addr not in index:
            continue
        r, i = index[addr]
        w = r.words[i]
        terms = []
        for f in p.fields.values():
            v = w.chosen.get(f.name)
            if v is None or v is f.default:
                continue
            arg = ''
            if w.branch and v.param:
                arg = '(w%d)' % (rom[addr] >> p.signals[w.branch[0]].lo & p.signals[w.branch[0]].width)
            terms.append('%s=%s%s' % (f.name, v.name, arg))
        out.append('%02X  %0*X  %-14s %s'
                   % (addr, (p.width + 3) // 4, rom[addr],
                      '%s.%d' % (r.name, i), ' '.join(terms)))
    out += ['', '; slot']
    for code in sorted(p.opcodes):
        mnemonic, name, _ = p.opcodes[code]
        n = cycles(p, code)
        out.append('%X   %02X   %-5s %-6s %s cicli'
                   % (code, code * p.slot + p.entry, mnemonic, name,
                      n[0] if n[0] == n[1] else '%d/%d' % (n[0], n[1])))
    return '\n'.join(out) + '\n'


def blob(words, bits):
    n = (bits + 7) // 8
    out = bytearray()
    for w in words:
        for i in range(n):
            out.append(w >> (8 * i) & 0xFF)
    return base64.b64encode(bytes(out)).decode()


def patch(path, p, rom):
    text = open(path, encoding='utf-8').read()
    found = [m for m in re.finditer(r'<Memory\b[^>]*/>', text) if 'Note="uCode"' in m.group(0)]
    if len(found) != 1:
        raise SystemExit('il circuito non contiene una sola memoria Note="uCode"')
    old = found[0].group(0)
    addr_bits = max(1, (p.rom - 1).bit_length())
    new = old
    for attr, value in (('AddressBitWidth', addr_bits), ('DataBitWidth', p.width),
                        ('Data', blob(rom, p.width))):
        new = re.sub(r'%s="[^"]*"' % attr, '%s="%s"' % (attr, value), new, count=1)
    if new == old:
        print('uCode: nessuna modifica')
    open(path, 'w', encoding='utf-8').write(text.replace(old, new, 1))
    print('uCode: %d x %d bit scritte in %s' % (p.rom, p.width, path))


def report(p, rom, free):
    print('control word (%d bit)' % p.width)
    for s in sorted(p.signals.values(), key=lambda s: -s.hi):
        print('  %5s  %s' % (s.span(), s.name))
    if free:
        print('  liberi: ' + ', '.join(map(str, free)))
    print('\ncampi (il primo valore e\' il default)')
    for f in p.fields.values():
        print('  %-6s %s' % (f.name, ' | '.join(f.values)))
    print('\ncicli per macroistruzione')
    total = []
    for code in sorted(p.opcodes):
        mnemonic, name, _ = p.opcodes[code]
        n = cycles(p, code)
        total.append(max(n))
        print('  %X  %-5s %-6s %s' % (code, mnemonic, name,
                                      n[0] if n[0] == n[1] else '%d/%d' % (n[0], n[1])))
    print('  peggiore, media: %.2f' % (sum(total) / len(total)))
    used = sum(1 for r in p.routines.values() for _ in r.words)
    print('\nparole usate: %d/%d' % (used, p.rom))


def main():
    ap = argparse.ArgumentParser(description='compilatore del microcodice EVSCPU')
    ap.add_argument('source')
    ap.add_argument('-o', metavar='DIR', help='scrive ucode.hex e ucode.lst')
    ap.add_argument('-patch', metavar='FILE', help='scrive l\'immagine nel circuito')
    ap.add_argument('-report', action='store_true')
    args = ap.parse_args()

    try:
        p = parse(open(args.source, encoding='utf-8').read())
        owner = layout(p)
        rom = encode(p)
        errors, warnings, free = check(p, rom, owner)
    except Error as e:
        print('%s: %s' % (args.source, e), file=sys.stderr)
        return 1
    seen = set()
    errors = [e for e in errors if not (e in seen or seen.add(e))]
    for w in warnings:
        print('%s: attenzione: %s' % (args.source, w), file=sys.stderr)
    if errors:
        for e in errors:
            print('%s: errore: %s' % (args.source, e), file=sys.stderr)
        return 1

    if args.o:
        with open('%s/ucode.hex' % args.o, 'w') as f:
            f.write(''.join('%0*X\n' % ((p.width + 3) // 4, w) for w in rom))
        with open('%s/ucode.lst' % args.o, 'w') as f:
            f.write(listing(p, rom, owner))
    if args.patch:
        patch(args.patch, p, rom)
    if args.report:
        report(p, rom, free)
    return 0


if __name__ == '__main__':
    sys.exit(main())
