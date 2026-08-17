
.dw 0
.dw 0
.dw 0
.dw 0

.dw 0
.dw 0
.dw 0
.dw 0

.dw 0
.dw 0
.dw 0
.dw 0

.dw 0
.dw 0
.dw 0
.dw 0

.include "globals.s"

__shadow:   .dw 0xF

.include "boot.s"

__boot:     LIT     6
            STA     _arg0
            SHR     _arg0
            LIT     3
            SUB     _arg0
            JZE     .ok
            JMP     __init.hard_err
.ok:        LIT     __init.print
            STA     _ra
            JMP     __init
            
.include "lib.s"
.include "io.s"

__init:     LIT     1
			JZE     .hard_err			; one or both of LIT/JZE not working
            STA     __shadow
            LIT     0
            ADD     __shadow
            JZE     .hard_err           ; one or both of STA/ADD not working even in the base case
            LIT     4
            STA     __shadow
            LIT     5
            STA     __shadow
            LIT     5
            SUB     __shadow
            JZE     .selftest
            LIT     0x1                 ; nothing work
            JMP     .hard_err
            
.selftest:	LIT     0                   ; require working lit/sta/add/jze/jmp, test the other instructions    
            STA     __shadow
            LIT     10
            LDA     __shadow
            JZE     .oklda
            LIT     0x7                 ; Lda error
            JMP     .hard_err
.oklda:     LIT     3					
			STA     __shadow
			LIT     15
			ADD     __shadow
			LIT     3
			SUB     __shadow
			JZE     .oksub
			LIT     0x2		            ; Math error
			JMP     .hard_err
.oksub:		LIT     4
            STA     _ix0
            LIT     0
            AND     _ix0
            JZE     .okand
            LIT     0x3                 ; And error
            JMP     .hard_err
.okand:     LIT     0x0F
            STA     __shadow
            LIT     0xF0
            NOR     __shadow
            AND     _const_00FF         ; low byte of ~(0xF0|0x0F) must be 0
            JZE     .oknor
            LIT     0x4                 ; Nor error
            JMP     .hard_err
.oknor:     LIT     1
            JNZ     .okjnz
            LIT     0x5                 ; Comparison error
            JMP     .hard_err
.okjnz:     LIT     0
            STA     __shadow
            INC     __shadow
            LDA     __shadow
            JNZ     .okinc
            LIT     0x6                 ; Inc error
            JMP     .hard_err
.okinc:
;.okjpi:
;.okshr:
;.okldi:
;.oksti:

.print:     LIT     8
            STA     _arg0
            LIT     .emit0
            STA     _ra
            JMP     __bin2dec
.emit0:     LIT     0
            STA     _arg2
            LIT     .dg1
            STA     _ra
            JMP     __put_dec

.dg1:       LIT     46
            STA     _arg0
            LIT     .emit1
            STA     _ra
            JMP     __bin2dec
.emit1:     LIT     0
            STA     _arg2
            LIT     .dg2
            STA     _ra
            JMP     __put_dec

.dg2:       LIT     17
            STA     _arg0
            LIT     .emit2
            STA     _ra
            JMP     __bin2dec
.emit2:     LIT     3
            STA     _arg2
            LIT     .wait
            STA     _ra
            JMP     __put_dec

.wait:      LIT     0xF
            LIT     0xE
            LIT     0xD
            JZE     .hard_err
            JMP     .wait
            LIT     0xF
            LIT     0xE
            LIT     0xD
			
.hard_err:  LIT     0
            JMP     .hard_err
           