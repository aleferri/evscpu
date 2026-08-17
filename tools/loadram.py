#!/usr/bin/env python3
"""Scrive un binario assemblato nella RAM incorporata di EVSCPU.CircuitProject.

    loadram.py EVSCPU.CircuitProject apps/test.bin

Il binario deve essere assemblato con -endian=little, che e' l'ordine che
LogicCircuit usa nelle memorie: questo script non riordina niente. Tocca solo
l'attributo Data dell'unica Memory scrivibile del progetto, quindi nessuna
geometria e nessun filo. Un blob piu' corto della memoria viene completato con
zeri fino a coprire tutta la memoria.
"""

import base64
import re
import sys


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    circuit, binary = sys.argv[1], sys.argv[2]

    image = open(binary, 'rb').read()
    if len(image) % 2:
        raise SystemExit('%s: %d byte, non e\' un numero intero di parole a 16 bit'
                         % (binary, len(image)))
    words = [image[i] | image[i + 1] << 8 for i in range(0, len(image), 2)]

    src = open(circuit, encoding='utf-8').read()
    # la RAM non e' un elemento vuoto: il contenuto sta in un <Data> figlio,
    # spezzato su piu' righe, non in un attributo come nelle ROM
    # LogicCircuit scrive la RAM in due forme: elemento vuoto con attributo Data,
    # oppure elemento con un <Data> figlio. Vanno gestite entrambe.
    found = [m for m in re.finditer(
        r'<Memory\b[^>]*Writable="True"[^>]*?(?:/>|>.*?</Memory>)', src, re.S)]
    if len(found) != 1:
        raise SystemExit('il progetto non contiene una sola Memory scrivibile')
    old = found[0].group(0)
    head = re.sub(r'\s*/?>$', '>', old[:old.index('>') + 1])
    # via l'attributo Data della forma vuota, o resterebbe accanto al figlio
    # <Data> che scriviamo, e LogicCircuit leggerebbe quello vecchio
    head = re.sub(r'\s+Data="[^"]*"', '', head)

    bits = int(re.search(r'DataBitWidth="(\d+)"', head).group(1))
    size = 1 << int(re.search(r'AddressBitWidth="(\d+)"', head).group(1))
    if bits != 16:
        raise SystemExit('la RAM e\' a %d bit, questo script assume 16' % bits)
    if len(words) > size:
        raise SystemExit('%d parole non stanno in una RAM da %d' % (len(words), size))

    # l'immagine viene completata a tutta la memoria: il progetto tiene la RAM
    # per intero, e non voglio dipendere da come LogicCircuit tratta un blob
    # piu' corto della memoria che descrive
    used = len(words)
    words += [0] * (size - len(words))
    raw = base64.b64encode(b''.join(w.to_bytes(2, 'little') for w in words)).decode()
    blob = '\n'.join(raw[i:i + 76] for i in range(0, len(raw), 76))
    new = '%s\n\t\t<Data>%s</Data>\n\t</Memory>' % (head, blob)
    open(circuit, 'w', encoding='utf-8').write(src.replace(old, new, 1))
    print('%d parole scritte nella RAM da %d' % (used, size))


if __name__ == '__main__':
    sys.exit(main())
