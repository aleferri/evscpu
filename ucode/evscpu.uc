# Microcodice di EVSCPU. Compilato da tools/ucasm.py.
#
# La ROM e' divisa in uno slot per opcode. I quattro bit alti di uPC vengono da
# MIR, che inseguono IR salvo quando il microcodice lo congela con ir=save; i
# quattro bassi dal contatore, che il campo next carica con un indice di parola
# dentro lo slot corrente. Il dispatch entra sempre alla parola 'entry', quindi
# le parole basse di ogni slot non sono raggiungibili dal dispatch; quelle dello
# slot 0 sono raggiungibili solo dal reset e contengono il boot.
#
# Una routine che vuole fare il fetch in anticipo congela MIR con ir=save nella
# parola di fetch e lo libera con ir=pass nella propria ultima parola.

width 24
rom   256
slot  16
entry 4

# ---------------------------------------------------------------- control word

signal dr_rd   0
signal fetch   1
signal wm      2
signal pc_wa   3
signal dr_wa   4
signal lar     5
signal ldc     6
signal inc     7
signal pc_rd   8
signal ac_rd   9
signal tr_rd  10
signal bm     12:11
signal target 16:13
signal useq   18:17
signal save   19
signal pass   20

# Ogni campo occupa bit propri e ha un valore di default: uno stato elenca solo
# i campi che se ne discostano. I valori di un campo sono mutuamente esclusivi
# per costruzione, quindi due master sullo stesso bus o due operazioni di memoria
# nello stesso ciclo non sono esprimibili.

field mem   { none | read: dr_rd | fetch: fetch | write: wm }
field bus_a { none | pc: pc_wa | dr: dr_wa | const: ldc }
field ar    { hold | load: lar }
field pc    { hold | inc: inc | load: pc_rd | load_inc: pc_rd inc }
field ac    { hold | load: ac_rd }
field tr    { hold | load: tr_rd }
field bus2  { un: bm=0 | ac: bm=1 | fn: bm=2 | dr: bm=3 }
field next  { step: useq=0 | dispatch: useq=2 target=4 | goto(target): useq=2 | brz(target): useq=3 }
field ir    { follow | save: save | pass: pass }

# ------------------------------------------------------------------------ boot

# AR <- 0x100, poi la parola letta li' e' l'indirizzo d'ingresso, non
# un'istruzione: finisce in PC e in AR, e da li' parte il primo fetch.

routine boot {
    bus_a=const ar=load;
    mem=read;
    bus_a=dr ar=load pc=load;
    mem=fetch pc=inc next=dispatch;
}

at 0 boot

# -------------------------------------------------------------------- routines

# L'ultima parola di ogni routine fa il fetch dell'istruzione seguente e
# dispatcha: non esiste una coda di fetch condivisa.

routine alu {
    bus_a=dr ar=load;
    mem=read;
    bus2=fn ac=load tr=load bus_a=pc ar=load;
    mem=fetch pc=inc next=dispatch;
}

routine lit {
    bus2=dr ac=load tr=load bus_a=pc ar=load;
    mem=fetch pc=inc next=dispatch;
}

# Opcode non implementato: AR torna a PC e l'istruzione seguente parte, quindi
# si comporta da NOP invece di finire in stati indefiniti.

routine nop {
    bus_a=pc ar=load;
    mem=fetch pc=inc next=dispatch;
}

# INC e SHR differiscono solo per la funzione di AluMem, selezionata da IR[0].
# TR e' il dato scritto in memoria, quindi la scrittura non puo' caricarlo; la
# coda lo riporta ad AC perche' su TR si prova la condizione dei salti.

routine mal {
    bus_a=dr ar=load;
    mem=read;
    bus2=un tr=load;
    mem=write bus_a=pc ar=load;
    bus2=ac tr=load mem=fetch pc=inc next=dispatch;
}

routine jmp {
    bus_a=dr ar=load pc=load;
    mem=fetch pc=inc next=dispatch;
}

routine jpi {
    bus_a=dr ar=load;
    mem=read;
    bus_a=dr ar=load pc=load;
    mem=fetch pc=inc next=dispatch;
}

# AR <- PC copre il ramo non preso; il preso lo sovrascrive con il bersaglio.

routine jnz {
          bus_a=pc ar=load next=brz(skip);
          bus_a=dr ar=load pc=load;
    skip: mem=fetch pc=inc next=dispatch;
}

routine jze {
          bus_a=pc ar=load next=brz(take);
          mem=fetch pc=inc next=dispatch;
    take: bus_a=dr ar=load pc=load;
          mem=fetch pc=inc next=dispatch;
}

routine lda {
    bus_a=dr ar=load;
    mem=read;
    bus2=dr ac=load tr=load bus_a=pc ar=load;
    mem=fetch pc=inc next=dispatch;
}

routine ldi {
    bus_a=dr ar=load;
    mem=read;
    bus_a=dr ar=load;
    mem=read bus_a=pc ar=load;
    bus2=dr ac=load tr=load mem=fetch pc=inc next=dispatch;
}

routine sta {
    bus_a=dr ar=load;
    mem=write bus_a=pc ar=load;
    mem=fetch pc=inc next=dispatch;
}

routine sti {
    bus_a=dr ar=load;
    mem=read;
    bus_a=dr ar=load;
    mem=write bus_a=pc ar=load;
    mem=fetch pc=inc next=dispatch;
}

# --------------------------------------------------------------- mappa opcode

opcode 0x0 add = alu
opcode 0x1 sub = alu
opcode 0x2 and = alu
opcode 0x3 nor = alu
opcode 0x4 --- = nop
opcode 0x5 lit = lit
opcode 0x6 inc = mal
opcode 0x7 shr = mal
opcode 0x8 jmp = jmp
opcode 0x9 jpi = jpi
opcode 0xA jnz = jnz
opcode 0xB jze = jze
opcode 0xC lda = lda
opcode 0xD ldi = ldi
opcode 0xE sta = sta
opcode 0xF sti = sti
