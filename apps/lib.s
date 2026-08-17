 

; memcopy: src, dest, n
__memcopy:      LDA     _arg2
                JZE     .end
.loop:          STA     _arg2
                LDI     _arg0
                STI     _arg1
                INC     _arg0
                INC     _arg1
                LDA     _arg2
                SUB     _const_0001
                JNZ     .loop
.end:           JPI     _ra
                
                
; memset: c: int, dest: ptr, n: int
__memset:       LDA     _arg2
                JZE     .end
.loop:          STA     _arg2
                LDA     _arg0
                STI     _arg1
                INC     _arg1
                LDA     _arg2
                SUB     _const_0001
                JNZ     .loop
.end:           JPI     _ra
                

; convert a binary number to its decimal digits
; arg0: value (0..255), leaves hundreds in _g2, tens in _g1, units in _g0
__bin2dec:      LIT     0xFF
                AND     _arg0
                STA     _arg0
                LIT     _pow2_units         ; prepare units table
                STA     _ix0
                LIT     _pow2_tens          ; prepare tens table
                STA     _ix1
                LIT     _pow2_hundreds      ; prepare hundreds table
                STA     _ix2
                LIT     0
                STA     _g0                 ; units
                STA     _g1                 ; tens
                STA     _g2                 ; hundreds
.loop:          LDA     _arg0
                AND     _const_0001         ; check if n & 1 is true,
                JZE     .skip               ; otherwise skip to the next bit
                LDI     _ix0                ; read units table entry at [ix0]
                ADD     _g0                 ; add to the units
                STA     _g0
                LDI     _ix1                ; read tens table entry at [ix1]
                ADD     _g1                 ; add to the tens
                STA     _g1
                LDI     _ix2                ; read hundreds table entry at [ix2]
                ADD     _g2                 ; add to the hundreds
                STA     _g2
.skip:          INC     _ix0                ; advance units table pointer
                INC     _ix1                ; advance tens table pointer
                INC     _ix2                ; advance hundreds table pointer
                SHR     _arg0               ; shift right n
                LDA     _arg0
                JNZ     .loop               ; test not zero
.carry_units:   LDA     _g0
                SUB     _const_000A         ; units - 10
                AND     _const_8000         ; test sign bit
                JNZ     .carry_tens         ; units < 10, units done
                LDA     _g0
                SUB     _const_000A
                STA     _g0                 ; units -= 10
                INC     _g1                 ; carry into tens
                JMP     .carry_units
.carry_tens:    LDA     _g1
                SUB     _const_000A         ; tens - 10
                AND     _const_8000         ; test sign bit
                JNZ     .done               ; tens < 10, tens done
                LDA     _g1
                SUB     _const_000A
                STA     _g1                 ; tens -= 10
                INC     _g2                 ; carry into hundreds
                JMP     .carry_tens
.done:          JPI     _ra                 ; digits in _g2, _g1, _g0
