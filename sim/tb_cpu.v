// Fa girare il circuito esportato da LogicCircuit con la RAM caricata da
// apps/test.bin, e stampa una traccia confrontabile con quella dell'emulatore.
`timescale 1ns/1ps

module tb_cpu;
    reg Clock = 1'b0, R = 1'b0, wai = 1'b0;
    wire [15:0] DI, DO, ADR, pc;
    wire write;

    reg [15:0] mem [0:65535];
    integer i, fd, hi, lo, cicli;

    Extended_Very_Simple_CPU_Core dut (
        .DI(DI), .wai(wai), .R(R), .Clock(Clock),
        .DO(DO), .ADR(ADR), .write(write), .pc(pc));

    assign DI = mem[ADR];
    // write viene dal circuito: wm gatato col clock invertito, quindi l'impulso
    // nasce sul fronte di discesa quando AR e' stabile e finisce prima del
    // fronte di salita successivo. La RAM latcha sulla salita di write.
    wire wr_pulse = write;
    localparam LIMITE = 200000;                // oltre il quale si fallisce
    reg [3:0] digit [0:5];
    reg [5:0] written = 6'b000000;             // quali cifre sono state scritte
    reg done = 1'b0;
    // 46 sulle prime tre cifre, 17 sulle ultime tre: e' quello che test.s emette
    reg [3:0] atteso [0:5];
    reg traccia = 1'b0;
    always @(posedge wr_pulse) begin
        mem[ADR] <= DO;
        // il display risponde quando ADDR[15:4] sono tutti uno, e ADDR[2:0]
        // sceglie la cifra: modellarlo evita di prendere per riuscita una
        // scrittura a una periferica che non esiste
        if (ADR[15:4] == 12'hFFF && ADR[2:0] < 6) begin
            digit[ADR[2:0]] <= DO[3:0];
            written[ADR[2:0]] <= 1'b1;
            if (written == 6'b011111 && ADR[2:0] == 5) done <= 1'b1;
            $display("  DISPLAY  cifra %0d <= %0d", ADR[2:0], DO[3:0]);
        end else
            $display("  SCRITTURA  mem[%04X] <= %04X", ADR, DO);
    end
    always #5 Clock = ~Clock;

    reg [15:0] prev = 16'hFFFF;
    initial begin
        atteso[0] = 0; atteso[1] = 4; atteso[2] = 6;
        atteso[3] = 0; atteso[4] = 1; atteso[5] = 7;
        if ($test$plusargs("traccia")) traccia = 1'b1;
        for (i = 0; i < 65536; i = i + 1) mem[i] = 16'h0000;
        fd = $fopen("apps/test.bin", "rb");
        i = 0;                                     // fino a fine file, non a un
        lo = $fgetc(fd);                           // conteggio fisso
        while (lo != -1) begin
            hi = $fgetc(fd);                       // assemblato con -endian=little
            mem[i] = (hi << 8) | lo;
            i = i + 1;
            lo = $fgetc(fd);
        end
        $display("  caricate %0d parole", i);
        $fclose(fd);
        R = 1'b0;                                   // reset attivo basso
        repeat (4) @(posedge Clock);
        @(negedge Clock) R = 1'b1;
        $display("  ciclo   PC    ADR   DI    DO");
        cicli = 0;
        for (i = 0; i < LIMITE && !done; i = i + 1) begin
            cicli = i;
            @(negedge Clock);
            if (pc !== prev) begin
                if (traccia) $display("  %6d   %04X  %04X  %04X  %04X", i, pc, ADR, DI, DO);
                prev = pc;
            end
        end
        @(negedge Clock);

        if (!done) begin
            $display("\nFALLITO: nessuna uscita completa in %0d cicli, PC %04X", LIMITE, pc);
            $fatal(1);
        end
        for (i = 0; i < 6; i = i + 1)
            if (digit[i] !== atteso[i]) begin
                $display("\nFALLITO: cifra %0d vale %0d, atteso %0d", i, digit[i], atteso[i]);
                $fatal(1);
            end
        $display("\nSUPERATO in %0d cicli: display = %0d%0d%0d %0d%0d%0d",
                 cicli, digit[0], digit[1], digit[2], digit[3], digit[4], digit[5]);
        $finish;
    end
endmodule
