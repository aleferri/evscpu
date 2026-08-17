"""Geometria dei jam nel formato LogicCircuit, per i generatori in questa cartella.

Serve a scrivere fili a coordinate giuste: LogicCircuit non memorizza la posizione
dei punti di connessione, la calcola all'apertura dal contenuto del simbolo. Ogni
regola qui sotto e' MISURATA su simboli esistenti di EVSCPU.CircuitProject
confrontando gli estremi dei fili con l'origine del simbolo, e la riga di
provenienza dice su cosa. Non estrapolare senza misurare: due volte ho dedotto
una regola plausibile e due volte era sfasata di una cella.

Un filo che passa sopra un jam che non gli appartiene ci si CONNETTE, mentre due
fili che si incrociano senza estremo in comune no (misurato: 1307 incroci nel
progetto, nessuno fra fili della stessa rete). Quindi instradare vuol dire
evitare i jam altrui, non evitare gli incroci.
"""


def pin_in(x, y):
    """Pin d'ingresso: simbolo largo 2, jam a destra.

    Misurato sui pin del Microsequencer: simbolo (10,12), filo a (12,13).
    """
    return (x + 2, y + 1)


def pin_out(x, y):
    """Pin d'uscita (PinSide Right): jam a sinistra, riceve da sinistra.

    Misurato su upc del Microsequencer: simbolo (61,20), filo a (61,21).
    """
    return (x, y + 1)


def memory(x, y):
    """ROM non scrivibile: (indirizzo, dato). Indipendente dalle larghezze.

    Misurato su tutte e sei le Memory del progetto, da 4x8 a 16x16.
    """
    return (x, y + 2), (x + 3, y + 2)


def splitter(x, y, pin_count):
    """(pin stretti dal bit 0, pin largo). Il bit 0 e' quello piu' in alto.

    Misurato sullo splitter 16x16 della vecchia control unit: simbolo (45,24),
    stretti (46,25)..(46,40), largo (45,32).
    """
    return [(x + 1, y + 1 + k) for k in range(pin_count)], (x, y + pin_count // 2)


def gate(x, y, inputs):
    """(ingressi, uscita) di una porta primitiva.

    Misurato dentro Microprogram Counter IR: NOT (15,21) ingresso (15,23) uscita
    (18,23); AND2 (20,24) ingressi (20,25) e (20,27).
    """
    if inputs == 1:
        ins = [(x, y + 2)]
    elif inputs == 2:
        ins = [(x, y + 1), (x, y + 3)]
    else:
        ins = [(x, y + 1 + k) for k in range(inputs)]
    return ins, (x + 3, y + 2)


def side_span(count, size):
    """Posizioni dei pin lungo un lato, distribuite agli estremi.

    Un pin solo va al centro del lato; due o piu' partono da 1 con passo intero
    troncato, quindi l'ultimo non arriva necessariamente in fondo al lato.
    Misurato su Mux 2w 4 bit (2 pin, +1 +3, lato 4), Register 4 bit (3 pin,
    +1 +2 +3, lato 4; un pin a destra, +2), Microsequencer (9 pin, +1..+9, lato
    10; un pin a destra, +5), Microcode Control Unit (12 pin a destra, +1..+12,
    lato 13; 3 pin a sinistra, +1 +6 +11, cioe' passo 5 e non 5.5 arrotondato).
    """
    if count == 1:
        return [size // 2]
    step = (size - 2) // (count - 1)
    return [1 + k * step for k in range(count)]


def instance(x, y, left=0, right=0, top=0, bottom=0):
    """Jam di un'istanza di sottocircuito, per lato.

    L'ORDINE su un lato segue la posizione dei pin DENTRO il sottocircuito, non
    l'ordine di dichiarazione nel file: verificato su Register 4 bit, dove i pin
    sono dichiarati R, Q, D, LD, Clock e i jam a sinistra escono D, R, Clock.
    Sui lati verticali si ordina per y crescente, sugli orizzontali per x. Se due
    pin dello stesso lato hanno la stessa coordinata l'ordine e' indecidibile:
    spostarne uno nel sottocircuito invece di indovinare.

    Altezza e larghezza crescono col numero di pin del lato piu' popoloso, con un
    minimo di 4 in altezza e 3 in larghezza.
    """
    h = max(4, left + 1, right + 1)
    w = max(3, top + 1, bottom + 1)
    return dict(
        left=[(x, y + d) for d in side_span(left, h)],
        right=[(x + w, y + d) for d in side_span(right, h)],
        top=[(x + d, y) for d in side_span(top, w)],
        bottom=[(x + d, y + h) for d in side_span(bottom, w)],
        size=(w, h),
    )


# Istanze usate dai generatori, con i pin nell'ordine dei jam.
# Counter4b: E, LD e # a sinistra confermati in quest'ordine dall'autore; i due
# pin sotto (Clock, Ra) e i due sopra (I1, I0) hanno la stessa coordinata dentro
# il sottocircuito, quindi il loro ordine reciproco non e' ricavabile.
COUNTER4B = dict(left=['E', 'LD', '#'], right=['Q'], top=['I?', 'I?'],
                 bottom=['Clock?', 'Ra?'])
MICROSEQUENCER = dict(left=['clk', 'arst', 'target', 'w', 'useq', 'z', 'ir',
                            'save', 'pass'], right=['upc'])

# I pin di confine della control unit, nell'ordine dei jam sull'istanza dentro il
# Core. L'ordine dipende da DOVE stanno i simboli dei pin dentro la control unit,
# quindi spostarli sfasa i fili nel Core senza che il file smetta di aprirsi: le
# coordinate scelte da gencu.py sono parte dell'interfaccia, non estetica.
CONTROL_UNIT = dict(
    left=['W', 'Clock', 'RST'], top=['TR', 'IR'],
    right=['dr_rd', 'fetch', 'wm', 'pc_wa', 'dr_wa', 'lar', 'ldc', 'inc',
           'pc_rd', 'ac_rd', 'tr_rd', 'bm'])
