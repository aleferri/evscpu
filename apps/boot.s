; Vettore di reset. Il microcodice legge la parola a 0x100 e la carica in PC e in
; AR: quello che sta qui e' l'indirizzo del punto d'ingresso, non un'istruzione.
; Il punto d'ingresso e' la parola che segue, quindi chi include questo file deve
; farlo immediatamente prima di __boot. ADR emette la parola grezza: .dw non
; risolve le etichette.

.advance 0x0100

            ADR     __boot
