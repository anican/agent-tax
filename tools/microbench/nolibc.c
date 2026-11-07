/* nolibc.c — smallest possible process: no libc, no dynamic loader. Built with
   gcc -O2 -static -nostdlib -nostartfiles. Establishes the kernel-only floor of
   fork+exec+exit. */
void _start(void) {
  __asm__ volatile("mov $60, %eax\n xor %edi, %edi\n syscall");
}
