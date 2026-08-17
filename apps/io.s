; put a digit on the 4-digit 7-segment display
; arg0: digit value (0..15, hw decodes to segments)
; arg1: position (0..3), cell [_timer_ptr + arg1]
__put_digit:    LDA     _timer_ptr              ; display base
                ADD     _arg1               ; + position
                STA     _arg1               ; address of the target digit
                LDA     _arg0               ; digit value
                STI     _arg1               ; write it to the selected digit
                JPI     _ra

; emit the digits left by __bin2dec on three cells of the display
; arg2: position of the hundreds; tens and units follow
__put_dec:      LDA     _ra
                STA     _b0                 ; __put_digit uses _ra, save ours
                LDA     _arg2
                STA     _b1                 ; __put_digit overwrites _arg1
                STA     _arg1
                LDA     _g2
                STA     _arg0
                LIT     .tens
                STA     _ra
                JMP     __put_digit
.tens:          LDA     _b1
                ADD     _const_0001
                STA     _arg1
                LDA     _g1
                STA     _arg0
                LIT     .units
                STA     _ra
                JMP     __put_digit
.units:         LDA     _b1
                ADD     _const_0002
                STA     _arg1
                LDA     _g0
                STA     _arg0
                LIT     .back
                STA     _ra
                JMP     __put_digit
.back:          LDA     _b0
                STA     _ra
                JPI     _ra


__get_c:
