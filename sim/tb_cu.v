// Collaudo della control unit: verifica che ogni parola presenti i segnali
// previsti, che ogni routine termini con un fetch e che i conteggi di ciclo
// siano quelli dichiarati in docs/internals.txt.

`default_nettype none
`timescale 1ns/1ps

module tb_cu;

    reg         clk = 1'b0;
    reg         rst = 1'b1;
    reg         wait_n = 1'b0;
    reg  [3:0]  ir = 4'd0;
    reg  [15:0] tr = 16'd0;

    wire dr_rd, fetch, wm, pc_wa, dr_wa, lar, ldc, inc, pc_rd, ac_rd, tr_rd;
    wire [1:0] bm;
    wire [7:0] upc;

    integer errors = 0;

    evscpu_cu dut (
        .clk(clk), .rst(rst), .wait_n(wait_n), .ir(ir), .tr(tr),
        .dr_rd(dr_rd), .fetch(fetch), .wm(wm), .pc_wa(pc_wa), .dr_wa(dr_wa),
        .lar(lar), .ldc(ldc), .inc(inc), .pc_rd(pc_rd), .ac_rd(ac_rd),
        .tr_rd(tr_rd), .bm(bm), .upc(upc)
    );

    always #5 clk = ~clk;

    task step;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    // controlla che l'insieme dei segnali alti sia esattamente quello atteso
    task expect_word;
        input [7:0]  want_upc;
        input [12:0] want;      // {bm[1:0], tr_rd, ac_rd, pc_rd, inc, ldc, lar, dr_wa, pc_wa, wm, fetch, dr_rd}
        input [127:0] name;
        reg   [12:0] got;
        begin
            got = {bm, tr_rd, ac_rd, pc_rd, inc, ldc, lar, dr_wa, pc_wa, wm, fetch, dr_rd};
            if (upc !== want_upc || got !== want) begin
                $display("  FALLITO %0s: uPC=%02X atteso %02X, segnali=%013b attesi %013b",
                         name, upc, want_upc, got, want);
                errors = errors + 1;
            end else
                $display("  ok      %0s  uPC=%02X", name, upc);
        end
    endtask

    // percorre una routine dal dispatch al fetch successivo e conta i cicli
    task run_slot;
        input [3:0]  opcode;
        input        zero;
        input [31:0] want_cycles;
        input [127:0] name;
        integer n;
        begin
            ir <= opcode;
            tr <= zero ? 16'h0000 : 16'h0001;
            n = 1;                 // la parola d'ingresso e' il primo ciclo
            while (n < 20 && !(fetch === 1'b1)) begin
                step;
                n = n + 1;
                if (upc[7:4] !== opcode) begin
                    $display("  FALLITO %0s: uscito dallo slot, uPC=%02X", name, upc);
                    errors = errors + 1;
                    n = 100;
                end
            end
            if (n == 20) begin
                $display("  FALLITO %0s: nessun fetch in 20 cicli", name);
                errors = errors + 1;
            end else if (n < 100) begin
                if (n !== want_cycles) begin
                    $display("  FALLITO %0s: %0d cicli, attesi %0d", name, n, want_cycles);
                    errors = errors + 1;
                end else
                    $display("  ok      %0s  %0d cicli", name, n);
                if (inc !== 1'b1) begin
                    $display("  FALLITO %0s: fetch senza pc++", name);
                    errors = errors + 1;
                end
                step;   // consuma il dispatch
            end
        end
    endtask

    initial begin
        $display("boot");
        wait_n = 1'b0;
        repeat (2) @(posedge clk);
        @(negedge clk);
        rst = 1'b0;
        #1;
        //                        bm tr ac pcrd inc ldc lar drwa pcwa wm fe drrd
        expect_word(8'h00, 13'b00_0_0_0___0___1___1___0____0___0__0__0, "w0 ldc+lar");
        step;
        expect_word(8'h01, 13'b00_0_0_0___0___0___0___0____0___0__0__1, "w1 dr_rd");
        step;
        expect_word(8'h02, 13'b00_0_0_1___0___0___1___1____0___0__0__0, "w2 AR,PC<-DR");
        step;
        expect_word(8'h03, 13'b00_0_0_0___1___0___0___0____0___0__1__0, "w3 fetch+inc");

        $display("\nrouting per macroistruzione");
        ir = 4'd5;                 // il dispatch dopo il boot entra nello slot di IR
        step;
        run_slot(4'h5, 1'b1, 2, "LIT");
        run_slot(4'h0, 1'b1, 4, "ADD");
        run_slot(4'h8, 1'b1, 2, "JMP");
        run_slot(4'h9, 1'b1, 4, "JPI");
        run_slot(4'hC, 1'b1, 4, "LDA");
        run_slot(4'hE, 1'b1, 3, "STA");
        run_slot(4'h6, 1'b1, 5, "INC");
        run_slot(4'h7, 1'b1, 5, "SHR");
        run_slot(4'hD, 1'b1, 5, "LDI");
        run_slot(4'hF, 1'b1, 5, "STI");
        run_slot(4'hA, 1'b0, 3, "JNZ preso");
        run_slot(4'hA, 1'b1, 2, "JNZ non preso");
        run_slot(4'hB, 1'b1, 3, "JZE preso");
        run_slot(4'hB, 1'b0, 2, "JZE non preso");
        run_slot(4'h4, 1'b1, 2, "opcode illegale");

        $display("\n%0d errori", errors);
        if (errors == 0) $display("COLLAUDO SUPERATO");
        $finish;
    end

endmodule

`default_nettype wire
