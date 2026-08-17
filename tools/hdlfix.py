#!/usr/bin/env python3
"""Rende compilabile l'export HDL di LogicCircuit.

    hdlfix.py cartella_export sim/hdl

L'export e' fedele nella logica ma non e' Verilog valido: un nome di modulo
contiene spazi, e dove piu' uscite pilotano lo stesso filo i tri-state vengono
resi come concatenazioni invece che come net condivise. Qui si correggono solo
questi artefatti, nessuna modifica al circuito.
"""

import glob
import re
import os
import sys


def convert(name, t):
    # nome di modulo con spazi
    t = t.replace('module Microcode Control Unit_ROM_34x22',
                  'module Microcode_Control_Unit_ROM_34x22')
    t = t.replace('Microcode Control Unit_ROM_34x22_34x22', 'ucode_rom_34x22')
    t = t.replace('Microcode Control Unit_ROM_34x22', 'Microcode_Control_Unit_ROM_34x22')

    if name == 'Address_Bus_Control':
        # BA e' pilotato dentro (la costante via ldc) e fuori (PC e DR)
        t = t.replace('input[15:0]\tBA', 'inout[15:0]\tBA').replace('.D({BA, BA})', '.D(BA)')

    if name == 'Main_Unit':
        t = t.replace('output[15:0]\tBA', 'inout[15:0]\tBA')
        # i quattro tri-state del bus 2 pilotano un solo filo
        for p in ('Pin50x9', 'Pin50x16', 'Pin50x28', 'Pin61x9'):
            t = t.replace('wire[15:0] %s;\n' % p, '').replace('.Q(%s)' % p, '.Q(bus2)')
        t = t.replace('.D({Pin61x9, Pin50x28, Pin50x16, Pin50x9})', '.D(bus2)')
        t = t.replace('\twire[15:0] Pin14x29;', '\ttri[15:0] bus2;\n\twire[15:0] Pin14x29;')

    if name == 'Data_Register':
        # splitter e merger dello schema: l'uscita del registro e il bus
        # ricomposto sono due net distinte, l'export le fonde in una sola e
        # produce un anello combinatorio sul nibble alto
        t = t.replace('\twire Pin21x12;',
                      '\twire [15:0] raw;\n\tassign Q[11:0] = raw[11:0];\n\twire Pin21x12;')
        t = t.replace('\t\t.Q(Q),\n\t\t.LD(Pin21x12)', '\t\t.Q(raw),\n\t\t.LD(Pin21x12)')
        t = t.replace('.Div(Q[15:12])', '.Div(raw[15:12])')

    if name == 'Microcode_Control_Unit':
        # la ROM esportata e' congelata al momento dell'export: il banco deve
        # leggere l'immagine corrente, o si simula un microcodice vecchio
        t = re.sub(r'\n\t\tmemory\[\d+\] = \d+;', '', t)
        t = t.replace('\tinitial begin',
                      '\tinitial begin\n\t\t$readmemh("ucode/ucode.hex", memory);')

    if name == 'Extended_Very_Simple_CPU_Core':
        t = t.replace('wire[15:0] Pin30x14;', 'tri[15:0] Pin30x14;')
    return t


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in sorted(glob.glob(os.path.join(src, '*.sv'))):
        name = os.path.basename(f)[:-3]
        t = open(f, encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
        open(os.path.join(dst, name + '.v'), 'w').write(convert(name, t))
        n += 1
    print('%d file convertiti in %s' % (n, dst))


if __name__ == '__main__':
    sys.exit(main())
