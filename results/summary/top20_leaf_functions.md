| # | Leaf function | DSO | Category | % of on-CPU samples |
|---|---|---|---|---|
| 1 | `_PyEval_EvalFrameDefault` | python3.11 | core logic | 9.64 |
| 2 | `[unknown]` | python3.11 | unclassified | 7.71 |
| 3 | `gc_collect_main` | python3.11 | allocation | 5.29 |
| 4 | `_PyEval_EvalFrameDefault` | python3.11 | interpreter startup/imports | 4.27 |
| 5 | `recently_deleted` | [kernel.kallsyms] | filesystem metadata | 3.50 |
| 6 | `lookup_bh_lru` | [kernel.kallsyms] | filesystem metadata | 2.24 |
| 7 | `_PyObject_Malloc` | python3.11 | allocation | 2.13 |
| 8 | `visit_decref` | python3.11 | allocation | 2.09 |
| 9 | `visit_reachable` | python3.11 | allocation | 1.56 |
| 10 | `_PyObject_Free` | python3.11 | allocation | 1.37 |
| 11 | `rep_movs_alternative` | [kernel.kallsyms] | memory movement | 1.35 |
| 12 | `__memmove_evex_unaligned_erms` | libc.so.6 | memory movement | 1.08 |
| 13 | `PyUnicode_InternInPlace` | python3.11 | interpreter startup/imports | 1.00 |
| 14 | `PyObject_GenericGetAttr` | python3.11 | core logic | 0.97 |
| 15 | `type_new` | python3.11 | interpreter startup/imports | 0.89 |
| 16 | `clear_page_erms` | [kernel.kallsyms] | memory movement | 0.87 |
| 17 | `__brelse` | [kernel.kallsyms] | filesystem metadata | 0.78 |
| 18 | `r_object` | python3.11 | interpreter startup/imports | 0.66 |
| 19 | `[unknown]` | libz.so.1.3 | unclassified | 0.65 |
| 20 | `_int_malloc` | libc.so.6 | allocation | 0.65 |
