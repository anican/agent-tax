| # | Leaf function | DSO | Category | % of on-CPU samples |
|---|---|---|---|---|
| 1 | `[unknown]` | cc1 | core logic | 15.10 |
| 2 | `_PyEval_EvalFrameDefault` | python3.11 | core logic | 6.13 |
| 3 | `file_cache_slot::get_next_line(char**, long*)` | cc1 | core logic | 5.86 |
| 4 | `[unknown]` | cc1plus | core logic | 4.83 |
| 5 | `gc_collect_main` | python3.11 | allocation | 3.65 |
| 6 | `PyObject_GenericGetAttr` | python3.11 | core logic | 2.33 |
| 7 | `_int_malloc` | libc.so.6 | allocation | 1.15 |
| 8 | `__pyx_f_7sklearn_7metrics_29_pairwise_distances_reduction_21_middle_term_computer__middle_term_sparse_sparse_64(__Pyx_memviewslice, __Pyx_memviewslice, __Pyx_memviewslice, long, long, __Pyx_memviewslice, __Pyx_memviewslice, __Pyx_memviewslice, long, long, double*)` | _middle_term_computer.cpython-311-x86_64-linux-gnu.so | core logic | 1.08 |
| 9 | `visit_decref` | python3.11 | allocation | 0.96 |
| 10 | `_PyObject_Malloc` | python3.11 | allocation | 0.96 |
| 11 | `clear_page_erms` | [kernel.kallsyms] | memory movement | 0.86 |
| 12 | `bitmap_set_bit(bitmap_head*, int)` | cc1 | core logic | 0.84 |
| 13 | `_PyEval_EvalFrameDefault` | python3.11 | interpreter startup/imports | 0.80 |
| 14 | `[unknown]` | libgomp.so.1.0.0 | unclassified | 0.79 |
| 15 | `visit_reachable` | python3.11 | allocation | 0.70 |
| 16 | `__memmove_evex_unaligned_erms` | libc.so.6 | memory movement | 0.68 |
| 17 | `_PyObject_Free` | python3.11 | allocation | 0.63 |
| 18 | `__memset_evex_unaligned_erms` | libc.so.6 | memory movement | 0.58 |
| 19 | `[unknown]` | x86_64-linux-gnu-as | unclassified | 0.57 |
| 20 | `rep_movs_alternative` | [kernel.kallsyms] | memory movement | 0.51 |
