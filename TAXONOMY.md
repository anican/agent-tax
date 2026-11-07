# TAXONOMY.md — mapping sampled leaf functions to categories

Generated from `tools/taxonomy.py` (`python tools/taxonomy.py --markdown`);
the code is the source of truth. Inputs per sample: the leaf function and
its DSO, the process name (`comm`), the innermost syscall on the kernel
stack, and context flags derived from the whole call chain
(`tools/perfparse.py`):

| Flag | Set when any frame on the stack is ... |
|---|---|
| `import` | `PyImport_*`, `_PyImport_*`, `import_find_and_load`, `_imp_*`, `import_name`, `builtin___import__` |
| `pystartup` | `pymain_init`, `Py_InitializeFromConfig`, `pyinit_main`, `init_interp_main`, `pyinit_core`, `init_importlib`, ... |
| `pyfini` | `Py_FinalizeEx`, `finalize_modules`, `_PyImport_Fini`, `Py_Exit`, `pymain_free` |
| `pycompile` | `_PyAST_Compile`, `Py_CompileString*`, `builtin_compile`, `_PyPegen_run_parser`, `compiler_*`, `_PyParser_*` |
| `pf` | `exc_page_fault`, `asm_exc_page_fault`, `handle_mm_fault` |
| `irq` | interrupt / softirq entry frames |
| `ldso` | any frame in `ld-linux*.so` or a `_dl_*` symbol |
| `exec` / `fork` / `exit` | `load_elf_binary`/`bprm_execve`; `copy_process`/`kernel_clone`; `do_exit`/`exit_mmap`/`mmput` |

Syscall sets used by the rules:
- process lifecycle: clone, clone3, execve, execveat, exit, exit_group, fork, vfork, wait4, waitid
- filesystem metadata: access, chdir, chmod, chown, close, close_range, creat, faccessat, faccessat2, fchdir, fchmod, fchmodat, fchown, fchownat, fgetxattr, flistxattr, fstat, fstatat64, fstatfs, futimesat, getcwd, getdents, getdents64, getxattr, inotify_add_watch, inotify_init1, inotify_rm_watch, lchown, lgetxattr, link, linkat, listxattr, llistxattr, lstat, mkdir, mkdirat, newfstat, newfstatat, newlstat, newstat, open, openat, openat2, readlink, readlinkat, rename, renameat, renameat2, rmdir, stat, statfs, statx, symlink, symlinkat, umask, unlink, unlinkat, utime, utimensat, utimes
- scheduling: clock_nanosleep, futex, futex_waitv, nanosleep, sched_yield
- heap/mapping management: brk, madvise, mmap, mprotect, mremap, munmap

## Rules (first match wins)

| Order | Rule | Category | Subcategory | Scope | Matches |
|---|---|---|---|---|---|
| 1 | U0a | other user-space | shell / glue (stripped binary) | user | unresolved leaf inside a stripped shell/glue binary (bash, sh, timeout, tee, ...): the whole binary is shell glue |
| 2 | U0b | core logic | cli tool (stripped binary) | user | unresolved leaf inside a stripped CLI tool binary (git, grep, sed, find, ...): the tool's own code |
| 3 | U0c | core logic | compiler (stripped binary) | user | unresolved leaf inside a compiler/assembler/linker binary |
| 4 | U0d | compression | zlib/lzma/bz2/zstd (stripped library) | user | unresolved leaf inside libz/libzstd/liblzma/libbz2: single-purpose compression libraries |
| 5 | U0e | hashing/crypto | libcrypto/libssl (stripped library) | user | unresolved leaf inside libcrypto/libssl (TLS for downloads, hashing) |
| 6 | U0f | scheduling/context switch | OpenMP runtime (stripped libgomp) | user | unresolved leaf inside libgomp (GNU OpenMP runtime): its internal code is barrier/spin-wait/team management, i.e. thread orchestration; the parallel work itself runs in the caller's code |
| 7 | U0 | unclassified | unresolved symbol | user | leaf symbol unresolved (`[unknown]`) or DSO unknown |
| 8 | K1 | memory movement | kernel copy/zero | kernel | kernel leaf: clear_page*, copy_page*, copy_user*, rep_movs/stos_alternative, mem{cpy,move,set}, copy_{to,from}_user, folio zeroing |
| 9 | U1 | memory movement | libc mem* | user | user leaf: mem{cpy,move,set}*, mempcpy, wmem*, bzero (incl. libc IFUNC variants such as __memmove_evex_unaligned_erms) |
| 10 | K2 | allocation | kernel page/slab alloc | kernel | kernel leaf: page allocator (__alloc_pages, get_page_from_freelist, rmqueue, free_pages...), slab (kmem_cache_*, kmalloc/kfree), memcg charging, LRU insertion |
| 11 | U2 | allocation | malloc / pymalloc / GC | user | user leaf: libc malloc family, C++ new/delete, CPython obmalloc (_PyObject_Malloc/Free, pymalloc_*), CPython cyclic GC (gc_collect_main, visit_*, *_traverse) |
| 12 | K3 | hashing/crypto | kernel crc/hash | kernel | kernel leaf: crc32*, sha*, blake2s, chacha, siphash, jhash |
| 13 | U3 | compression | zlib/lzma/bz2/zstd | user | user leaf in libz/libzstd/liblzma/libbz2 or CPython zlib/_lzma/_bz2 modules, or inflate*/deflate*/adler32/longest_match |
| 14 | K4 | compression | kernel compression | kernel | kernel leaf: lz4/zstd/zlib/lzo |
| 15 | U4 | hashing/crypto | sha/md5/siphash | user | user leaf in libcrypto/libssl/_hashlib/_sha*/_md5/_blake2, git's sha1dc (sha1_compression_states, ubc_check), CPython siphash/_Py_HashBytes/unicode_hash, crc32 |
| 16 | U5 | serialization/parsing | json/pickle/xml/struct | user | user leaf in _json/_pickle/pyexpat/libexpat/_csv/_struct/_elementtree, or JSON scanner/encoder symbols |
| 17 | U6a | interpreter startup/imports | source compile / unmarshal (under import) | user | CPython tokenizer/PEG parser/AST/compiler/assembler or marshal (r_object/w_object) leaf, with an import or interpreter-init frame on the stack |
| 18 | U6b | serialization/parsing | python source compile / marshal (not under import) | user | same leaves as U6a without an import/init frame (e.g. compile()/exec of strings, doctest, marshal outside import) |
| 19 | U6v | virtualization-related | CPUID VM exits in glibc CPU-feature detection | user | ld.so/libc CPU-feature and cache-size detection (intel_check_word, handle_intel, get_common_cache_info, init_cpu_features, update_active...): CPUID-bound code run at every process start; CPUID traps to the hypervisor (~11 us per call measured in this guest), so nearly all of this time is VM-exit cost |
| 20 | U7 | process lifecycle | dynamic linking / libc start & exit | user | user leaf in ld-linux*.so, or libc start/exit/fork/exec/_dl_* symbols |
| 21 | U8 | process lifecycle | python interpreter teardown | user | interpreter leaf with Py_FinalizeEx/finalize_modules/Py_Exit on the stack (module teardown at exit) |
| 22 | U9 | scheduling/context switch | locks / GIL / sleeps | user | user leaf: pthread mutex/cond/rwlock/once, futex wrappers, semaphores, CPython GIL (take_gil/drop_gil, PyCOND_*/PyMUTEX_*, PyThread_*), sleeps |
| 23 | U10 | interpreter startup/imports | import machinery & module execution | user | interpreter leaf (python binary/libpython/extension module) with an import frame (PyImport_*, import_find_and_load, _imp_*, builtin___import__) or interpreter-init frame (pymain_init, Py_InitializeFromConfig, init_interp_main...) on the stack |
| 24 | K5 | virtualization-related | paravirt / KVM / virtio | kernel | kernel leaf: pv_*, __pv_queued_spin_*, kvm_*, kvmclock/pvclock, virtio*/vring*/virtqueue*, hypercall paths |
| 25 | K6 | scheduling/context switch | scheduler / futex | kernel | kernel leaf in the scheduler (schedule, __switch_to, finish_task_switch, pick_next*, enqueue/dequeue*, update_curr, ttwu*, psi_*), futex code, or any kernel leaf under futex/sched_yield/nanosleep syscalls |
| 26 | K7 | process lifecycle | exec/fork/exit/wait syscalls | kernel | any kernel leaf under execve/clone/clone3/fork/vfork/exit/exit_group/wait4/waitid, or leaf in mm teardown/copy (unmap_page_range, zap_pte_range, copy_page_range, exit_mmap, load_elf_binary...) |
| 27 | K8 | process lifecycle | page fault handling | kernel | kernel leaf with exc_page_fault/handle_mm_fault on the stack, or a fault-path leaf (do_user_addr_fault, filemap_map_pages, set_pte_range, next_uptodate_folio, lock_vma_under_rcu...) |
| 28 | K9 | process lifecycle | mmap/mprotect for dynamic loading | kernel | kernel leaf under mmap/munmap/mprotect/brk with ld.so frames on the user stack |
| 29 | K10 | allocation | mmap/brk/madvise (heap management) | kernel | kernel leaf under brk/mmap/munmap/mremap/madvise/mprotect without ld.so frames |
| 30 | K11 | filesystem metadata | path lookup / stat / open / readdir | kernel | kernel leaf under a metadata syscall (stat family, access, open/openat/close, getdents64, readlink, getcwd, chdir, mkdir/unlink/rename, utimensat, chmod...), or a path-walk/dcache/readdir leaf |
| 31 | K12 | other kernel | other kernel | kernel | any other kernel leaf (data read/write, pipes, signals, timers, interrupts/softirqs, networking...) |
| 32 | U11 | core logic | python interpreter / extensions | user | remaining user leaf in a python process in the interpreter, an extension module, libm/BLAS/libstdc++ (the program's own work) |
| 33 | U12 | core logic | compiler | user | remaining user leaf in a compiler/assembler/linker process (cc1, cc1plus, as, ld, collect2, lto1, clang) |
| 34 | U13 | core logic | cli tool (git/grep/sed/...) | user | remaining user leaf in git, grep, rg, sed, cat, find, head/tail, wc, ls... (their own binary, libc string/regex routines, libpcre) |
| 35 | U14 | other user-space | shell / glue / misc libc | user | remaining user leaf in bash/sh/timeout/tee/env, the vDSO, or libc routines not covered above (stdio, getenv, qsort, strtol, locale...) |

## Notes

- **CPUID in a microVM (rule U6v, added after measurement; DECISIONS.md D16).**
  glibc's CPU-feature/cache-size detection in ld.so executes CPUID dozens of
  times per process start. In this guest one CPUID costs ~11 µs (VM exit;
  `tools/microbench/cpuid_cost.c`), and ~67% of a `/bin/true` start is spent
  in these functions. Their samples are therefore counted as
  *virtualization-related*, not as dynamic linking. The report gives H4 both
  ways.

- **Leaf-first.** A specific leaf (memcpy, malloc, sha1, inflate, ...) wins over
  any stack context; context only disambiguates generic leaves (interpreter
  code, generic kernel code). Inclusive, stack-based totals (everything under
  an import, under a page fault, under a metadata syscall, ...) are reported
  separately in the report (`results/summary/inclusive_context_shares.csv`).
- **UNCLASSIFIED** = samples whose user-space leaf symbol is unresolved
  (`[unknown]`) inside a multi-purpose DSO (libc, an interpreter, an
  unknown library). Unresolved leaves inside *single-purpose* stripped
  binaries/libraries are attributed by DSO (rules U0a–U0f: bash → shell glue,
  git/grep/sed → CLI tool core, cc1/as/ld → compiler, libz → compression,
  libcrypto → hashing/crypto, libgomp → OpenMP thread orchestration).
- **Kernel threads** (kworker, ksoftirqd, jbd2, ...) are classified with the
  same rules but reported as a separate group, not as part of the command.
- Regular expressions for every rule are in `tools/taxonomy.py`
  (`K_*` for kernel leaves, `U_*` for user-space leaves, `*_DSO` for DSO
  name patterns).
