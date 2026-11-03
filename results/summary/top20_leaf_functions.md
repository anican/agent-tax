| # | Leaf function | DSO | Category | % of on-CPU samples |
|---|---|---|---|---|
| 1 | `_PyEval_EvalFrameDefault` | python3.11 | core logic | 10.60 |
| 2 | `gc_collect_main` | python3.11 | allocation | 6.33 |
| 3 | `_PyEval_EvalFrameDefault` | python3.11 | interpreter startup/imports | 4.87 |
| 4 | `_PyObject_Malloc` | python3.11 | allocation | 2.68 |
| 5 | `visit_decref` | python3.11 | allocation | 2.45 |
| 6 | `visit_reachable` | python3.11 | allocation | 1.86 |
| 7 | `_PyObject_Free` | python3.11 | allocation | 1.74 |
| 8 | `rep_movs_alternative` | [kernel.kallsyms] | memory movement | 1.60 |
| 9 | `clear_page_erms` | [kernel.kallsyms] | memory movement | 1.41 |
| 10 | `PyUnicode_InternInPlace` | python3.11 | interpreter startup/imports | 1.24 |
| 11 | `__memmove_evex_unaligned_erms` | libc.so.6 | memory movement | 1.14 |
| 12 | `PyObject_GenericGetAttr` | python3.11 | core logic | 1.11 |
| 13 | `type_new` | python3.11 | interpreter startup/imports | 1.06 |
| 14 | `assemble` | python3.11 | serialization/parsing | 0.89 |
| 15 | `r_object` | python3.11 | interpreter startup/imports | 0.78 |
| 16 | `inflate_fast` | python3.11 | compression | 0.77 |
| 17 | `PyObject_GenericGetAttr` | python3.11 | interpreter startup/imports | 0.70 |
| 18 | `_int_malloc` | libc.so.6 | allocation | 0.69 |
| 19 | `dict_traverse` | python3.11 | allocation | 0.61 |
| 20 | `_PyFunction_Vectorcall` | python3.11 | core logic | 0.61 |
