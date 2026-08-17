// Microcode Control Unit di EVSCPU, equivalente Verilog-2005 del progetto.
//
// Scritto dalla specifica, non estratto dal disegno: modella la ROM, il
// sequencer e la testa di uPC come sono progettati, quindi mette alla prova il
// microcodice e la logica di controllo. Un filo sbagliato nello schema di
// LogicCircuit non si vede da qui.
//
// L'immagine di microcodice arriva da ucode/ucode.hex, prodotto da tools/ucasm.py.

`default_nettype none

module evscpu_cu #(
    parameter UCODE = "ucode/ucode.hex"
) (
    input  wire        clk,
    input  wire        rst,      // asincrono, attivo alto
    input  wire        wait_n,   // ferma il sequencer quando alto
    input  wire [3:0]  ir,       // opcode latchato
    input  wire [15:0] tr,       // sorgente della condizione

    output wire        dr_rd,
    output wire        fetch,
    output wire        wm,
    output wire        pc_wa,
    output wire        dr_wa,
    output wire        lar,
    output wire        ldc,
    output wire        inc,
    output wire        pc_rd,
    output wire        ac_rd,
    output wire        tr_rd,
    output wire [1:0]  bm,
    output wire [7:0]  upc       // esposto per il collaudo
);

    // ---------------------------------------------------------------- uPC

    // Testa: i quattro bit alti inseguono IR, e il microcodice li congela con
    // save per poter fare il fetch in anticipo, li libera con pass. hold e'
    // stato e non un'uscita diretta della ROM, altrimenti l'anello
    // combinatorio uPC -> ROM -> hold -> uPC si chiuderebbe.
    reg [3:0] saved;
    reg       hold;
    wire [3:0] s4 = hold ? saved : ir;

    reg [3:0] q;                       // contatore, quattro bit bassi
    assign upc = {s4, q};

    // ------------------------------------------------------------ ROM 256x24

    reg [23:0] ucode [0:255];
    initial $readmemh(UCODE, ucode);

    wire [23:0] cw = ucode[upc];

    assign dr_rd = cw[0];
    assign fetch = cw[1];
    assign wm    = cw[2];
    assign pc_wa = cw[3];
    assign dr_wa = cw[4];
    assign lar   = cw[5];
    assign ldc   = cw[6];
    assign inc   = cw[7];
    assign pc_rd = cw[8];
    assign ac_rd = cw[9];
    assign tr_rd = cw[10];
    assign bm    = cw[12:11];

    wire [3:0] target = cw[16:13];
    wire [1:0] useq   = cw[18:17];
    wire       save   = cw[19];
    wire       pass   = cw[20];

    // ------------------------------------------------------------- sequencer

    wire z  = (tr == 16'h0000);
    wire ld = useq[1] & (~useq[0] | z);   // useq: 0 avanza, 2 carica, 3 carica se z
    wire e  = ~wait_n;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            q     <= 4'd0;
            saved <= 4'd0;
            hold  <= 1'b0;
        end else begin
            if (ld)     q <= target;
            else if (e) q <= q + 4'd1;

            if (~save) saved <= ir;
            hold <= (hold & ~pass) | save;
        end
    end

endmodule

`default_nettype wire
