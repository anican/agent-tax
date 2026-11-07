/* spawnbench.c — fork+execve+waitpid a command N times from a C launcher (no
   shell in the loop) and print mean wall time per spawn in microseconds.
   usage: spawnbench N prog [args...]   (env is inherited) */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <sys/wait.h>
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
int main(int argc, char **argv){
  int n = atoi(argv[1]); double t0 = now();
  for (int i = 0; i < n; i++) {
    pid_t p = fork();
    if (p == 0) { execv(argv[2], argv + 2); _exit(127); }
    int st; waitpid(p, &st, 0);
    if (!WIFEXITED(st) || WEXITSTATUS(st) != 0) { fprintf(stderr, "child failed\n"); return 1; }
  }
  printf("%.1f us/spawn (n=%d)\n", (now() - t0) / n * 1e6, n); return 0;
}
