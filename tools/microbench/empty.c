/* empty.c — int main(){return 0;}; built once static (glibc, no ld.so) and once
   dynamic (ld.so + libc.so). Both run glibc's init_cpu_features/cacheinfo. */
int main(void) { return 0; }
