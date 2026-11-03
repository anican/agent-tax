/* cpuid_cost.c — cost of the CPUID instruction in this guest.
 * In a KVM guest CPUID unconditionally causes a VM exit to the hypervisor,
 * so it is far more expensive than on bare metal (~100-200 cycles). glibc's
 * ld.so runs CPUID many times at every process start (init_cpu_features,
 * intel_check_word / handle_intel for cache sizes via leaf 2 and leaf 4).
 * Also measures a plain loop of RDTSC-free arithmetic as a reference. */
#include <cpuid.h>
#include <stdio.h>
#include <time.h>
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
int main(void){
  unsigned a,b,c,d; const int N=200000; volatile unsigned sink=0;
  unsigned leaves[3]={0,2,4};
  for(int l=0;l<3;l++){
    double t0=now();
    for(int i=0;i<N;i++){ __cpuid_count(leaves[l],0,a,b,c,d); sink+=a^b^c^d; }
    double t1=now();
    printf("cpuid leaf %u: %.1f ns/call\n",leaves[l],(t1-t0)/N*1e9);
  }
  double t0=now(); for(int i=0;i<N*100;i++) sink+=i*7; double t1=now();
  printf("reference add loop: %.2f ns/iter\n",(t1-t0)/(N*100)*1e9);
  return 0;
}
