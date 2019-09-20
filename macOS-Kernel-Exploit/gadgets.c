// ROP Helpers

void __attribute__((naked)) swapgs() {
    __asm__ __volatile__("swapgs; ret ");
}