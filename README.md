# evscpu
Extended Very Simple CPU

Because i have too much free time (not really, shed a tear)

## ISA
Basically an 8 instruction, very unconfortable and awkward, CPU: the kind you get into trouble if you are seen with. While it won't fetch and execute you right away (or your program), as it isn't currently working there are speculations that it will, at some point.

The instruction set is an expansion of the very simple cpu, so the first four were set in stone (ADD, AND, STA, JMP), the next four are a basic requirement for even toy programs: SUB, JZE, LIT, NOR.
Since the cpu still seems to work, i added also INC, LDI and STI with plans for SHR, JPI and ADL

## Memory
Is a grid of 2^16 * 16 bit cells, only 2^12 are directly addressable inside each opcode, the rest need indirect access. 
The easiest organization is:
- ~4K words Program Memory
- ~60K words Data

## Opcodes
- ADD: add the content of the memory address to AC
- SUB: subtract the content of the memory address from AC
- AND: and the content of the memory address to AC
- NOR: nor the content of the memory address to AC
- LIT: load a constant
- (ADL): add a constant to AC
- INC: increase the content of the memory address in-place
- (SHR): shift right the content of the memory address in-place
- JMP: jump to the specified location
- (JPI): jump to the content of the specified location
- JZE: Jump if AC is zero
- (JNS): Jump if AC has negative bit set
- LDA: Load the content at the cell
- LDI: Load the content pointed by the location in AC
- STA: Store the content of AC in the specified location
- STI: Store the content of AC in the pointed position of the specified location
