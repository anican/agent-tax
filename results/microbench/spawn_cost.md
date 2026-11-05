| Target | What runs | wall µs/spawn | CPU µs/spawn | Δ CPU vs previous row |
|---|---|---|---|---|
| nolibc | no libc, no ld.so (`exit` syscall only) | 137 ± 5 | 114 ± 3 |  |
| static_glibc | `int main(){return 0;}`, static glibc (no ld.so) | 768 ± 8 | 709 ± 8 | +595 |
| dynamic_glibc | same, dynamically linked (ld.so + libc.so) | 884 ± 23 | 811 ± 21 | +102 |
| dynamic_glibc_tunables | dynamic, with `GLIBC_TUNABLES` cache sizes set | 870 ± 11 | 799 ± 11 | -12 |
| bin_true | `/bin/true` | 909 ± 13 | 832 ± 11 | +33 |
| grep_small | `grep -q main` on a 1-line file | 1089 ± 18 | 993 ± 14 | +161 |
| python_S_c_pass | `python -S -c pass` (no site) | 8788 ± 3875 | 6434 ± 235 | +5441 |
| python_I_c_pass | `python -I -c pass` (isolated, site on) | 8576 ± 316 | 8119 ± 33 | +1685 |
| python_c_pass | `python -c pass` | 8441 ± 132 | 8173 ± 122 | +54 |
| python_import_json | `python -c "import json,re,os"` | 16113 ± 1418 | 14848 ± 204 | +6675 |
