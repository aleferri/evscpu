#!/usr/bin/env python3
"""Ricostruisce il corpo di Microcode Control Unit dentro EVSCPU.CircuitProject.

I pin di confine restano quelli che sono, con gli stessi PinId: cambia solo cosa
c'e' dentro. Dopo la ROM non c'e' nessuna porta, i ventiquattro bit vanno diretti
ai pin d'uscita o a un merger.

    gencu.py EVSCPU.CircuitProject

La geometria dei jam e' misurata sulle istanze esistenti del progetto, non
dedotta: vedi JAM piu' sotto. Lo script rifiuta di scrivere se due reti diverse
condividono una coordinata o se un estremo di filo cade dentro un altro filo.
"""

import re
import sys
import uuid

import lcgeom

G = lambda: str(uuid.uuid4())

# bit della control word -> pin d'uscita, nell'ordine in cui escono dallo
# splitter, cosi' ogni collegamento e' un filo orizzontale singolo
DIRECT = ['dr_rd', 'fetch', 'wm', 'pc_wa', 'dr_wa', 'lar', 'ldc', 'inc',
          'pc_rd', 'ac_rd', 'tr_rd']
# gli altri bit: 11:12 bm, 13:16 target, 17:18 useq, 19 save, 20 pass


class Cu:
    def __init__(self, path):
        self.path = path
        self.src = open(path, encoding='utf-8').read()
        self.cu = self.circuit('Microcode Control Unit')
        self.useq = self.circuit('Microsequencer')
        self.test0 = self.circuit('Test = 0')
        self.rom = re.search(r'<Memory[^>]*Note="uCode"[^>]*/>', self.src).group(0)
        self.romid = re.search(r'MemoryId="([^"]*)"', self.rom).group(1)
        self.pins = dict(re.findall(
            r'<Pin PinId="([^"]*)" CircuitId="%s"[^>]*Name="([^"]*)"' % self.cu, self.src))
        self.pins = {name: pid for pid, name in self.pins.items()}
        self.elems, self.wires, self.nets = [], [], {}

    def circuit(self, name):
        m = re.search(r'LogicalCircuitId="([^"]*)"[^>]*Name="%s"' % re.escape(name), self.src)
        if not m:
            raise SystemExit('nel progetto non c\'e\' il circuito %r' % name)
        return m.group(1)

    # ----------------------------------------------------------- costruzione
    def sym(self, cid, x, y):
        self.elems.append('<CircuitSymbol CircuitSymbolId="%s" CircuitId="%s" '
                          'LogicalCircuitId="%s" X="%d" Y="%d" />' % (G(), cid, self.cu, x, y))

    def pin(self, name, x, y):
        """Ripiazza un pin di confine e torna il suo jam."""
        if name not in self.pins:
            raise SystemExit('la control unit non ha il pin %r' % name)
        self.sym(self.pins[name], x, y)
        out = 'PinType="Output"' in re.search(
            r'<Pin PinId="%s"[^>]*/>' % self.pins[name], self.src).group(0)
        return (lcgeom.pin_out if out else lcgeom.pin_in)(x, y)

    def splitter(self, bits, pc, x, y):
        sid = G()
        self.elems.append('<Splitter SplitterId="%s" BitWidth="%d" PinCount="%d" '
                          'Clockwise="True" />' % (sid, bits, pc))
        self.sym(sid, x, y)
        return lcgeom.splitter(x, y, pc)

    def net(self, name, *pts):
        self.nets.setdefault(name, []).append(pts)
        for a, b in zip(pts, pts[1:]):
            if a[0] != b[0] and a[1] != b[1]:
                raise SystemExit('%s: tratto obliquo %s %s' % (name, a, b))
            self.wires.append('<Wire WireId="%s" LogicalCircuitId="%s" X1="%d" Y1="%d" '
                              'X2="%d" Y2="%d" />' % (G(), self.cu, a[0], a[1], b[0], b[1]))

    # ------------------------------------------------------------- verifica
    def check(self, jams):
        def inner(p, a, b):
            if a[0] == b[0] == p[0]:
                return min(a[1], b[1]) < p[1] < max(a[1], b[1])
            if a[1] == b[1] == p[1]:
                return min(a[0], b[0]) < p[0] < max(a[0], b[0])
            return False

        def hits(p, pts):
            return any(inner(p, a, b) for a, b in zip(pts, pts[1:]))

        bad = set()
        for n1, runs1 in self.nets.items():
            for n2, runs2 in self.nets.items():
                if n1 == n2:
                    continue
                for pts1 in runs1:
                    for pts2 in runs2:
                        for p in pts1:
                            if p in pts2:
                                bad.add('%s e %s condividono %s' % (n1, n2, p))
                            if hits(p, pts2):
                                bad.add('estremo di %s dentro il filo di %s a %s' % (n1, n2, p))
        # un jam attraversato da un filo che non gli appartiene e' una
        # connessione involontaria, ed e' invisibile sul disegno
        for name, jam in jams.items():
            owner = [n for n, runs in self.nets.items() if any(jam in p for p in runs)]
            if len(owner) != 1:
                bad.add('il jam %s (%s) e\' collegato a %d reti' % (jam, name, len(owner)))
            for n, runs in self.nets.items():
                if n not in owner:
                    for pts in runs:
                        if hits(jam, pts):
                            bad.add('la rete %s passa dentro il jam %s (%s)' % (n, jam, name))
        return sorted(bad)

    # ---------------------------------------------------------------- uscita
    def write(self):
        src = self.src
        # via il corpo vecchio: simboli e fili della control unit, e la tabella
        # di dispatch che non serve piu'
        src = re.sub(r'\t<CircuitSymbol[^>]*LogicalCircuitId="%s"[^>]*/>\n' % self.cu, '', src)
        src = re.sub(r'\t<Wire[^>]*LogicalCircuitId="%s"[^>]*/>\n' % self.cu, '', src)
        old = re.search(r'\t<Memory[^>]*AddressBitWidth="4"[^>]*DataBitWidth="6"[^>]*/>\n', src)
        if old:
            src = src.replace(old.group(0), '')
        body = '\t' + '\n\t'.join(self.elems + self.wires) + '\n'
        open(self.path, 'w', encoding='utf-8').write(
            src.replace('</CircuitProject>', body + '</CircuitProject>'))


def build(c):
    jams = {}

    def J(name, jam):
        jams[name] = jam
        return jam

    # Le coordinate dei pin di confine determinano l'ordine dei jam sull'istanza
    # della control unit dentro il Core: cambiarle sfasa quel cablaggio in
    # silenzio. L'ordine atteso e' in lcgeom.CONTROL_UNIT.
    tr = J('TR', c.pin('TR', 2, 4))
    ir = J('IR', c.pin('IR', 2, 8))
    wait = J('W', c.pin('W', 2, 12))
    clock = J('Clock', c.pin('Clock', 2, 16))
    rst = J('RST', c.pin('RST', 2, 20))

    # rilevatore di zero su TR
    c.sym(c.test0, 8, 4)
    t0 = lcgeom.instance(8, 4, left=1, right=1)
    t0_in, t0_out = J('Test.T', t0['left'][0]), J('Test.=0', t0['right'][0])

    # sequencer: nove jam a sinistra nell'ordine della posizione interna dei pin
    c.sym(c.useq, 16, 26)
    order = lcgeom.MICROSEQUENCER
    box = lcgeom.instance(16, 26, left=len(order['left']), right=1)
    us = {n: J('USEQ.' + n, box['left'][k]) for k, n in enumerate(order['left'])}
    upc = J('USEQ.upc', box['right'][0])

    # ROM e splitter del dato
    c.sym(c.romid, 30, 22)
    a, d = lcgeom.memory(30, 22)
    addr, data = J('ROM.addr', a), J('ROM.data', d)
    bits, wide = c.splitter(24, 24, 40, 12)
    for i, b in enumerate(bits[:21]):
        J('bit%d' % i, b)
    J('splitter.bus', wide)

    # pin d'uscita allineati ai bit: un filo orizzontale ciascuno
    for i, name in enumerate(DIRECT):
        p = J(name, c.pin(name, 70, 12 + i))
        c.net(name, bits[i], p)
    bm = J('bm', c.pin('bm', 70, 36))

    c.net('rom.data', data, wide)
    c.net('rom.addr', upc, (24, upc[1]), (24, 24), addr)

    # merger: i bit entrano dai pin stretti, il bus esce da quello largo
    def merger(name, x, y, count, srcbits, escapes, dest):
        narrow, w = c.splitter(count, count, x, y)
        for k in range(count):
            J('%s.%d' % (name, k), narrow[k])
        J('%s.bus' % name, w)
        for k, (b, ex) in enumerate(zip(srcbits, escapes)):
            c.net('%s.b%d' % (name, k), bits[b], (ex, 13 + b), (ex, narrow[k][1]), narrow[k])
        c.net('%s.bus' % name, w, *dest)
        return w

    # i merger stanno sotto la fascia percorsa dai fili che li alimentano, cosi'
    # nessuna orizzontale di fuga attraversa i loro jam
    merger('bm', 76, 40, 2, [11, 12], [78, 79], [(76, 37), bm])
    merger('useq', 76, 46, 2, [17, 18], [80, 81], [(74, 47), (74, 52), (11, 52),
                                                   (11, 31), us['useq']])
    merger('target', 76, 54, 4, [13, 14, 15, 16], [82, 83, 84, 85],
           [(75, 56), (75, 60), (9, 60), (9, 29), us['target']])

    c.net('save', bits[19], (86, 32), (86, 62), (13, 62), (13, 34), us['save'])
    c.net('pass', bits[20], (87, 33), (87, 63), (14, 63), (14, 35), us['pass'])

    # ingressi del sequencer, un corridoio verticale ciascuno
    c.net('tr->test', tr, (6, 5), (6, 6), t0_in)
    c.net('z', t0_out, (12, 6), (12, 32), us['z'])
    c.net('clk', clock, (7, 17), (7, 27), us['clk'])
    c.net('arst', rst, (8, 21), (8, 28), us['arst'])
    c.net('w', wait, (10, 13), (10, 30), us['w'])
    c.net('ir', ir, (15, 9), (15, 33), us['ir'])
    return jams


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    c = Cu(sys.argv[1])
    jams = build(c)
    bad = c.check(jams)
    if bad:
        print('verifica fallita, non scrivo:', file=sys.stderr)
        print('\n'.join('  ' + b for b in bad), file=sys.stderr)
        return 1
    c.write()
    print('control unit: %d simboli, %d fili, %d jam tutti collegati una volta'
          % (len(c.elems), len(c.wires), len(jams)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
