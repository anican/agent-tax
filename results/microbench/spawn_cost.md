| Target | What runs | wall µs/spawn | CPU µs/spawn |
|---|---|---|---|
| nolibc | no libc, no ld.so (`exit` syscall only) | 137 ± 5 | 114 ± 3 |
| static_musl | `int main(){return 0;}`, **musl** static (no cache probing at start-up) | 176 ± 13 | 150 ± 13 |
| dynamic_musl | same, musl dynamic (musl ld.so) | 236 ± 7 | 197 ± 4 |
| static_glibc | same, **glibc** static (no ld.so) | 768 ± 8 | 709 ± 8 |
| static_glibc_recheck | glibc static, re-measured in the musl session (control) | 788 ± 11 | 724 ± 9 |
| dynamic_glibc | glibc dynamic (ld.so + libc.so) | 884 ± 23 | 811 ± 21 |
| dynamic_glibc_tunables | glibc dynamic, `GLIBC_TUNABLES` cache sizes set | 870 ± 11 | 799 ± 11 |
| bin_true | `/bin/true` | 909 ± 13 | 832 ± 11 |
| grep_small | `grep -q main` on a 1-line file | 1089 ± 18 | 993 ± 14 |
| python_S_c_pass | `python -S -c pass` (no site) | 8788 ± 3875 | 6434 ± 235 |
| python_I_c_pass | `python -I -c pass` (isolated, site on) | 8576 ± 316 | 8119 ± 33 |
| python_c_pass | `python -c pass` | 8441 ± 132 | 8173 ± 122 |
| python_import_json | `python -c "import json,re,os"` | 16113 ± 1418 | 14848 ± 204 |
