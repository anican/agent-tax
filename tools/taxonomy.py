"""taxonomy.py — map a sampled leaf function (+ stack context) to a category.

Input key (from perfparse.py): (group, comm, leaf_sym, leaf_dso, syscall, ctx)
Output: (category, subcategory, rule_id)

Rules are evaluated in order; the first match wins ("leaf first, then
context"). The same RULES table is rendered into TAXONOMY.md by
`python tools/taxonomy.py --markdown`, so the documentation cannot drift
from the code.
"""
import re, sys

CORE = "core logic"
CATS = [CORE, "memory movement", "allocation", "compression", "hashing/crypto",
        "serialization/parsing", "process lifecycle", "interpreter startup/imports",
        "filesystem metadata", "scheduling/context switch", "virtualization-related",
        "other kernel", "other user-space", "unclassified"]
ORCH = CATS[1:12]   # orchestration categories in the user's taxonomy (+ other kernel)

def R(p): return re.compile(p)

# ---------- symbol / dso patterns ----------
K_MEMMOVE = R(r"^(clear_page|copy_page|copy_user|rep_movs_alternative|rep_stos_alternative|_?_?mem(cpy|move|set)|memcpy_orig|copy_mc|_?copy_(to|from)_user|__?clear_user|csum_partial_copy|folio_zero|zero_user|copy_folio|clear_huge_page|copy_highpage|copy_subpage|clear_subpage)")
K_ALLOC = R(r"^(__alloc_pages|alloc_pages|__alloc_frozen|alloc_frozen|get_page_from_freelist|rmqueue|__rmqueue|free_pages|__free_pages|free_unref|free_pcppages_bulk|__free_one_page|free_frozen|kmem_cache_alloc|kmem_cache_free|__kmem_cache|__kmalloc|kmalloc|kfree|krealloc|kvmalloc|kvfree|slab_|___slab_alloc|__slab_alloc|__slab_free|alloc_slab|new_slab|vma_alloc_folio|folio_alloc|__folio_alloc|release_pages|__mem_cgroup_charge|mem_cgroup_charge|__memcg|memcg_|mod_memcg|try_charge|page_counter|uncharge|folios_put|__folio_put|free_pages_and_swap_cache|lru_add|folio_add_lru|__lruvec|lru_gen|mod_objcg|obj_cgroup|refill_obj_stock|consume_obj_stock|__pcs_replace|__put_partials|put_cpu_partial|___slab|__slab|alloc_pages_mpol|__alloc_pages_noprof|kmem_cache_alloc_noprof|__kmalloc_noprof|kmalloc_trace)")
K_HASH = R(r"^(crc32|__crc32|crc_|chksum|sha1_|sha256|sha512|sha3|blake2s|chacha|_sha|crypto_|md5|siphash|__siphash|hsiphash|jhash|xxh)")
K_COMPRESS = R(r"^(lz4|LZ4|zstd|ZSTD|zlib_|deflate|inflate|lzo)")
K_VIRT = R(r"^(pv_|__pv_|kvm_|__kvm|kvmclock|pvclock|xen_|vring_|virtqueue|virtio|vp_notify|vp_|vm_notify|hv_|__raw_callee_save___pv|__raw_callee_save___kvm|paravirt|hypercall|vsock|virtio_transport|virtnet|sev_|tdx_)")
K_SCHED = R(r"^(schedule|__schedule|preempt_schedule|__switch_to|switch_mm|finish_task_switch|pick_next|pick_task|put_prev|set_next|enqueue_|dequeue_|update_curr|update_load|update_cfs|__update_load|try_to_wake_up|ttwu|select_task_rq|select_idle|wake_up|__wake_up|psi_|load_balance|sched_|newidle_balance|update_rq_clock|check_preempt|resched|reweight|place_entity|futex|__futex|get_futex|hrtimer_wakeup|do_nanosleep|cpuacct|__calc_delta|update_min_vruntime|avg_vruntime|raw_spin_rq|prepare_task_switch|context_switch|activate_task|wakeup_preempt|perf_event_task_sched|__perf_event_task_sched|vruntime_eligible|pick_eevdf|__pick_eevdf|update_se|set_next_entity|put_prev_entity|__enqueue_entity|__dequeue_entity|task_mm_cid|mm_cid|__mm_cid)")
K_PF = R(r"^(do_user_addr_fault|exc_page_fault|asm_exc_page_fault|handle_mm_fault|__handle_mm_fault|handle_pte_fault|do_anonymous_page|do_fault|do_read_fault|do_cow_fault|do_shared_fault|do_wp_page|wp_page_copy|filemap_map_pages|next_uptodate|set_pte_range|lock_vma_under_rcu|__do_fault|filemap_fault|do_set_pte|finish_fault|do_pte_missing|__pte_offset_map|pte_offset_map|folio_add_new_anon|folio_add_file_rmap|__folio_add|__folio_mod_stat|__mod_lruvec|mm_counter|sync_mm_rss|__count_memcg|count_memcg|filemap_get_entry|__filemap_get_folio|vmf_|fault_|mas_walk|mtree_range_walk|__lruvec_stat_mod_folio)")
K_LIFE = R(r"^(unmap_page_range|zap_pte_range|zap_pmd_range|zap_pud_range|unmap_vmas|unmap_single_vma|copy_page_range|copy_pte_range|copy_pmd_range|copy_p4d_range|free_pgtables|free_pgd_range|exit_mmap|mmput|__mmput|load_elf_binary|begin_new_exec|bprm_|do_execveat|copy_process|dup_mm|dup_mmap|dup_task_struct|do_exit|do_group_exit|release_task|wait_consider_task|do_wait|exit_|mm_init|anon_vma_|unlink_anon_vmas|unlink_file_vma|vm_area_dup|vm_area_free|__vm_area_free|tlb_finish_mmu|tlb_flush_mmu|tlb_batch|free_swap_cache|page_remove_rmap|folio_remove_rmap|__tlb_remove|set_mm_exe_file|elf_load|elf_map|setup_arg_pages|copy_strings|__get_user_pages|get_user_pages|get_arg_page|mm_release|exit_files|put_files_struct|close_files)")
K_FSMETA = R(r"^(link_path_walk|path_|__d_lookup|d_lookup|lookup_|walk_component|filename_|getname|putname|dput|__dput|d_alloc|inode_permission|generic_permission|step_into|complete_walk|terminate_walk|may_open|do_dentry_open|do_open|do_filp_open|vfs_open|ext4_lookup|ext4_readdir|ext4_htree|ext4_get_inode|ext4_getattr|ext4_file_open|ext4_find_entry|__ext4_find_entry|ext4_search_dir|ext4_match|vfs_getattr|vfs_statx|cp_new_stat|cp_statx|do_statx|vfs_fstat|dcache_readdir|iterate_dir|filldir|verify_dirent|__ext4_read_dirblock|htree_dirblock|call_filldir|ext4fs_dirhash|str2hashbuf|d_hash|full_name_hash|hash_name|__legitimize|legitimize|try_to_unlazy|nd_jump|follow_|pick_link|security_inode|security_file_open|apparmor|aa_|fsnotify|__fsnotify|alloc_empty_file|__fput|fput|____fput|file_close|filp_close|close_fd|alloc_fd|fd_install|get_unused_fd|__alloc_fd|path_openat|open_last_lookups|set_root|lockref|__mnt_|mntput|mntget|atime_needs_update|touch_atime|ext4_dirty_inode|kernfs_|proc_|pid_revalidate|tid_fd_revalidate|d_revalidate|ovl_)")
FS_META_SC = set("""stat lstat fstat newstat newlstat newfstat newfstatat statx fstatat64 access faccessat faccessat2
open openat openat2 creat close close_range getdents getdents64 readlink readlinkat getcwd chdir fchdir mkdir mkdirat
rmdir unlink unlinkat rename renameat renameat2 link linkat symlink symlinkat utime utimes utimensat futimesat chmod
fchmod fchmodat chown fchown fchownat lchown inotify_add_watch inotify_rm_watch inotify_init1 statfs fstatfs
getxattr lgetxattr fgetxattr listxattr llistxattr flistxattr umask""".split())
LIFE_SC = set("execve execveat clone clone3 fork vfork exit exit_group wait4 waitid".split())
SCHED_SC = set("futex futex_waitv sched_yield nanosleep clock_nanosleep".split())
MEMMGMT_SC = set("brk mmap munmap mremap madvise mprotect".split())

U_MEMMOVE = R(r"^_*(mem(cpy|move|set)|mempcpy|wmem(cpy|move|set)|bzero|bcopy|explicit_bzero)")
U_ALLOC = R(r"^(malloc|free|calloc|realloc|_int_malloc|_int_free|_int_realloc|malloc_consolidate|tcache|_int_memalign|__libc_(malloc|free|calloc|realloc|memalign)|cfree|unlink_chunk|sysmalloc|systrim|arena_|alloc_perturb|__posix_memalign|posix_memalign|aligned_alloc|memalign|_mid_memalign|_Znwm|_ZdlPv|_Znam|_ZdaPv|operator new|operator delete|"
            r"_PyObject_(Malloc|Calloc|Realloc|Free)|PyObject_(Malloc|Calloc|Realloc|Free)|PyMem_|_PyMem_|pymalloc_|_PyObject_GC_(New|NewVar|Alloc|Link|Resize|TRACK)|gc_alloc|PyObject_GC_(Del|Track|UnTrack)|"
            r"gc_collect|deduce_unreachable|visit_decref|visit_reachable|subtract_refs|update_refs|move_unreachable|move_legacy_finalizers|handle_legacy_finalizers|finalize_garbage|delete_garbage|gc_collect_main|gc_collect_with_callback|gc_collect_generations|_PyGC_|gc_list_|"
            r"new_arena|allocate_from_new_pool|insert_to_freepool|_PyObject_ArenaMmap|_PyObject_ArenaMunmap|address_in_range|arena_map_|.*_traverse$|.*traverse$)")
U_COMPRESS_DSO = R(r"(libz\.so|libzstd|liblzma|libbz2|zlib\.cpython|_lzma\.cpython|_bz2\.cpython|_zstd|libdeflate|libbrotli|_brotli)")
U_COMPRESS = R(r"^(inflate|deflate|adler32|crc32_z|longest_match|lzma_|BZ2_|ZSTD_|zstd|compress_block|fill_window|updatewindow|build_tree|send_tree)")
U_HASH_DSO = R(r"(libcrypto|libssl|_hashlib\.cpython|_sha1\.cpython|_sha256\.cpython|_sha512\.cpython|_sha2\.cpython|_sha3\.cpython|_md5\.cpython|_blake2\.cpython)")
U_HASH = R(r"^(sha1|SHA1|sha256|SHA256|sha512|SHA512|blake2|BLAKE2|md5|MD5|_?sha1dc|ubc_check|sha1_compression|block_data_order|Keccak|EVP_|ossl_|_Py_HashBytes|siphash|pysiphash|unicode_hash|_Py_HashDouble|hash_bytes|xxh|XXH|fnv|crc32)")
U_SER_DSO = R(r"(_json\.cpython|_pickle\.cpython|pyexpat\.cpython|libexpat|libyaml|_yaml|libxml2|lxml|_csv\.cpython|_struct\.cpython|_elementtree)")
U_SER = R(r"^(scanstring|scan_once|_?encoder_|py_scanstring|_json|json_|XML_|PyXML|doContent|normal_|little2_|big2_|_Pickle|Pickler|Unpickler)")
U_PYCOMPILE = R(r"^(_PyPegen|_PyParser|_PyTokenizer|tok_|.*_rule$|_loop[01]_|_gather_|_tmp_\d+|compiler_|_PyCompile|assemble|_PyAST_|PyAST_|astfold_|fold_|symtable_|_PySymtable|optimize_|makecode|_PyCode_|stackdepth|label_exception|mark_reachable|write_location|insert_superinstructions|cfg_|basicblock_|instr_|validate_|_PyFuture|future_|unicode_decode_utf8|decode_unicode_with_escapes|parsestr|_PyUnicode_DecodeUnicodeEscape|ast_|PyAST|_PyArena|PyArena|r_object|r_long|r_string|r_ref|r_byte|r_short|r_float|read_object|PyMarshal_|marshal_|_PyMarshal|w_object|w_ref|w_long|w_string|w_complex_object|w_short|w_pstring|w_flush)")
U_LIFE = R(r"^(_dl_|__libc_start|__libc_fork|_Fork$|fork$|__spawn|posix_spawn|__posix_spawn|execve$|__execve$|_exit$|exit$|__run_exit_handlers|_IO_cleanup|__libc_early_init|__tunables|init_cacheinfo|intel_check|handle_intel|dl_|__dl|do_lookup_x|check_match|elf_|__libc_setup_tls|_dl_runtime|__GI__exit|__GI_exit|__libc_csu|_start$|_init$|_fini$)")
U_SCHED = R(r"^(GOMP_barrier|GOMP_parallel|gomp_barrier|gomp_team|gomp_thread|gomp_mutex|gomp_sem|pthread_mutex|pthread_cond|__pthread_mutex|__pthread_cond|___pthread|__lll_lock|__lll_unlock|lll_|__futex|futex_|sem_|__new_sem|pthread_once|__pthread_once|take_gil|drop_gil|PyCOND_|PyMUTEX_|_PyThread_|PyThread_|PyEval_RestoreThread|PyEval_SaveThread|_PyEval_SignalReceived|sched_yield|__sched_yield|pthread_spin|__pthread_spin|pthread_rwlock|__pthread_rwlock|clock_nanosleep|__clock_nanosleep|nanosleep|__nanosleep|usleep|__GI___clock_nanosleep|__pthread_clockjoin|pthread_join|_PyMutex|PyMutex|_PySemaphore|_PyParkingLot)")
U_LIBC_STR = R(r"^_*(mem(r)?chr|rawmemchr|str|wcs|wmem(chr|cmp)|memcmp|bcmp|__memcmp|__strn?cmp|__strn?casecmp|__strchr|__strlen|__strnlen|__strcpy|__stpcpy|re_search|re_|regexec|regcomp|dfa|kws|fgrep|__GI_str|__GI_mem)")
PY_DSO = R(r"(python3|libpython|\.cpython-3\d+|site-packages/|lib-dynload|numpy|scipy|sklearn|_sqlite3|libsqlite3|libm\.so|libm-|libgomp|libopenblas|libscipy_openblas|libgfortran|libstdc\+\+|libgcc_s|libffi|libuuid)")
COMPILER_COMM = R(r"^(cc1|cc1plus|as$|ld$|ld\.bfd|ld\.gold|collect2|lto1|lto-wrapper|clang|clang\+\+|gcc|g\+\+|cc$|c\+\+$|x86_64-linux-gnu-g|ccache)")
TOOL_COMM = R(r"^(git|git-|grep|rg|sed|cat|find|head|tail|wc|awk|mawk|gawk|ls|sort|diff|cut|uniq|xargs|tr|file|stat|less|nl|tree)")
SHELL_COMM = R(r"^(bash|sh$|dash|timeout|tee|env$|time$|perf-exec|replay_exec|run\.sh|truncate|date|jq|nohup|setsid)")
PY_COMM = R(r"^(python|pytest|pip|py\.test)")

def is_kernel(dso): return dso.startswith("[kernel") or dso == "[kernel.kallsyms]"

# ---------- ordered rules ----------
# each: (rule_id, category, subcategory, scope, description, predicate(k))
def _ctx(k): return set(k["ctx"].split("|")) if k["ctx"] else set()

STRIPPED_SHELL = R(r"/(bash|sh|dash|timeout|tee|env|time|truncate|date|jq)$")
STRIPPED_TOOL = R(r"/(git|git-[\w-]+|grep|rg|sed|cat|find|head|tail|wc|mawk|gawk|ls|sort|diff|cut|uniq|xargs|tr)$")
STRIPPED_CC = R(r"/(cc1|cc1plus|as|ld|ld\.bfd|ld\.gold|collect2|lto1|clang[\w.+-]*)$")

RULES = [
 ("U0a", "other user-space", "shell / glue (stripped binary)", "user", "unresolved leaf inside a stripped shell/glue binary (bash, sh, timeout, tee, ...): the whole binary is shell glue",
  lambda k: not k["kern"] and k["sym"].startswith("[unknown]") and STRIPPED_SHELL.search(k["dso"])),
 ("U0b", "core logic", "cli tool (stripped binary)", "user", "unresolved leaf inside a stripped CLI tool binary (git, grep, sed, find, ...): the tool's own code",
  lambda k: not k["kern"] and k["sym"].startswith("[unknown]") and STRIPPED_TOOL.search(k["dso"])),
 ("U0c", "core logic", "compiler (stripped binary)", "user", "unresolved leaf inside a compiler/assembler/linker binary",
  lambda k: not k["kern"] and k["sym"].startswith("[unknown]") and STRIPPED_CC.search(k["dso"])),
 ("U0d", "compression", "zlib/lzma/bz2/zstd (stripped library)", "user", "unresolved leaf inside libz/libzstd/liblzma/libbz2: single-purpose compression libraries",
  lambda k: not k["kern"] and k["sym"].startswith("[unknown]") and U_COMPRESS_DSO.search(k["dso"])),
 ("U0e", "hashing/crypto", "libcrypto/libssl (stripped library)", "user", "unresolved leaf inside libcrypto/libssl (TLS for downloads, hashing)",
  lambda k: not k["kern"] and k["sym"].startswith("[unknown]") and U_HASH_DSO.search(k["dso"])),
 ("U0f", "scheduling/context switch", "OpenMP runtime (stripped libgomp)", "user", "unresolved leaf inside libgomp (GNU OpenMP runtime): its internal code is barrier/spin-wait/team management, i.e. thread orchestration; the parallel work itself runs in the caller's code",
  lambda k: not k["kern"] and k["sym"].startswith("[unknown]") and "libgomp" in k["dso"]),
 ("U0", "unclassified", "unresolved symbol", "user", "leaf symbol unresolved (`[unknown]`) or DSO unknown",
  lambda k: not k["kern"] and (k["sym"].startswith("[unknown]") or k["dso"] in ("", "[unknown]"))),
 ("K1", "memory movement", "kernel copy/zero", "kernel", "kernel leaf: clear_page*, copy_page*, copy_user*, rep_movs/stos_alternative, mem{cpy,move,set}, copy_{to,from}_user, folio zeroing",
  lambda k: k["kern"] and K_MEMMOVE.match(k["sym"])),
 ("U1", "memory movement", "libc mem*", "user", "user leaf: mem{cpy,move,set}*, mempcpy, wmem*, bzero (incl. libc IFUNC variants such as __memmove_evex_unaligned_erms)",
  lambda k: not k["kern"] and U_MEMMOVE.match(k["sym"])),
 ("K2", "allocation", "kernel page/slab alloc", "kernel", "kernel leaf: page allocator (__alloc_pages, get_page_from_freelist, rmqueue, free_pages...), slab (kmem_cache_*, kmalloc/kfree), memcg charging, LRU insertion",
  lambda k: k["kern"] and K_ALLOC.match(k["sym"])),
 ("U2", "allocation", "malloc / pymalloc / GC", "user", "user leaf: libc malloc family, C++ new/delete, CPython obmalloc (_PyObject_Malloc/Free, pymalloc_*), CPython cyclic GC (gc_collect_main, visit_*, *_traverse)",
  lambda k: not k["kern"] and U_ALLOC.match(k["sym"])),
 ("K3", "hashing/crypto", "kernel crc/hash", "kernel", "kernel leaf: crc32*, sha*, blake2s, chacha, siphash, jhash",
  lambda k: k["kern"] and K_HASH.match(k["sym"])),
 ("U3", "compression", "zlib/lzma/bz2/zstd", "user", "user leaf in libz/libzstd/liblzma/libbz2 or CPython zlib/_lzma/_bz2 modules, or inflate*/deflate*/adler32/longest_match",
  lambda k: not k["kern"] and (U_COMPRESS_DSO.search(k["dso"]) or U_COMPRESS.match(k["sym"]))),
 ("K4", "compression", "kernel compression", "kernel", "kernel leaf: lz4/zstd/zlib/lzo",
  lambda k: k["kern"] and K_COMPRESS.match(k["sym"])),
 ("U4", "hashing/crypto", "sha/md5/siphash", "user", "user leaf in libcrypto/libssl/_hashlib/_sha*/_md5/_blake2, git's sha1dc (sha1_compression_states, ubc_check), CPython siphash/_Py_HashBytes/unicode_hash, crc32",
  lambda k: not k["kern"] and (U_HASH_DSO.search(k["dso"]) or U_HASH.match(k["sym"]))),
 ("U5", "serialization/parsing", "json/pickle/xml/struct", "user", "user leaf in _json/_pickle/pyexpat/libexpat/_csv/_struct/_elementtree, or JSON scanner/encoder symbols",
  lambda k: not k["kern"] and (U_SER_DSO.search(k["dso"]) or (PY_DSO.search(k["dso"]) and U_SER.match(k["sym"])))),
 ("U6a", "interpreter startup/imports", "source compile / unmarshal (under import)", "user", "CPython tokenizer/PEG parser/AST/compiler/assembler or marshal (r_object/w_object) leaf, with an import or interpreter-init frame on the stack",
  lambda k: not k["kern"] and PY_DSO.search(k["dso"]) and U_PYCOMPILE.match(k["sym"]) and (_ctx(k) & {"import", "pystartup"})),
 ("U6b", "serialization/parsing", "python source compile / marshal (not under import)", "user", "same leaves as U6a without an import/init frame (e.g. compile()/exec of strings, doctest, marshal outside import)",
  lambda k: not k["kern"] and PY_DSO.search(k["dso"]) and U_PYCOMPILE.match(k["sym"])),
 ("U7", "process lifecycle", "dynamic linking / libc start & exit", "user", "user leaf in ld-linux*.so, or libc start/exit/fork/exec/_dl_* symbols",
  lambda k: not k["kern"] and ("ld-linux" in k["dso"] or "/ld-" in k["dso"] or U_LIFE.match(k["sym"]))),
 ("U8", "process lifecycle", "python interpreter teardown", "user", "interpreter leaf with Py_FinalizeEx/finalize_modules/Py_Exit on the stack (module teardown at exit)",
  lambda k: not k["kern"] and "pyfini" in _ctx(k) and PY_DSO.search(k["dso"])),
 ("U9", "scheduling/context switch", "locks / GIL / sleeps", "user", "user leaf: pthread mutex/cond/rwlock/once, futex wrappers, semaphores, CPython GIL (take_gil/drop_gil, PyCOND_*/PyMUTEX_*, PyThread_*), sleeps",
  lambda k: not k["kern"] and U_SCHED.match(k["sym"])),
 ("U10", "interpreter startup/imports", "import machinery & module execution", "user", "interpreter leaf (python binary/libpython/extension module) with an import frame (PyImport_*, import_find_and_load, _imp_*, builtin___import__) or interpreter-init frame (pymain_init, Py_InitializeFromConfig, init_interp_main...) on the stack",
  lambda k: not k["kern"] and (_ctx(k) & {"import", "pystartup"}) and PY_DSO.search(k["dso"])),
 ("K5", "virtualization-related", "paravirt / KVM / virtio", "kernel", "kernel leaf: pv_*, __pv_queued_spin_*, kvm_*, kvmclock/pvclock, virtio*/vring*/virtqueue*, hypercall paths",
  lambda k: k["kern"] and K_VIRT.match(k["sym"])),
 ("K6", "scheduling/context switch", "scheduler / futex", "kernel", "kernel leaf in the scheduler (schedule, __switch_to, finish_task_switch, pick_next*, enqueue/dequeue*, update_curr, ttwu*, psi_*), futex code, or any kernel leaf under futex/sched_yield/nanosleep syscalls",
  lambda k: k["kern"] and (K_SCHED.match(k["sym"]) or k["sc"] in SCHED_SC)),
 ("K7", "process lifecycle", "exec/fork/exit/wait syscalls", "kernel", "any kernel leaf under execve/clone/clone3/fork/vfork/exit/exit_group/wait4/waitid, or leaf in mm teardown/copy (unmap_page_range, zap_pte_range, copy_page_range, exit_mmap, load_elf_binary...)",
  lambda k: k["kern"] and (k["sc"] in LIFE_SC or K_LIFE.match(k["sym"]) or (_ctx(k) & {"exec", "fork", "exit"}))),
 ("K8", "process lifecycle", "page fault handling", "kernel", "kernel leaf with exc_page_fault/handle_mm_fault on the stack, or a fault-path leaf (do_user_addr_fault, filemap_map_pages, set_pte_range, next_uptodate_folio, lock_vma_under_rcu...)",
  lambda k: k["kern"] and ("pf" in _ctx(k) or K_PF.match(k["sym"]))),
 ("K9", "process lifecycle", "mmap/mprotect for dynamic loading", "kernel", "kernel leaf under mmap/munmap/mprotect/brk with ld.so frames on the user stack",
  lambda k: k["kern"] and k["sc"] in MEMMGMT_SC and "ldso" in _ctx(k)),
 ("K10", "allocation", "mmap/brk/madvise (heap management)", "kernel", "kernel leaf under brk/mmap/munmap/mremap/madvise/mprotect without ld.so frames",
  lambda k: k["kern"] and k["sc"] in MEMMGMT_SC),
 ("K11", "filesystem metadata", "path lookup / stat / open / readdir", "kernel", "kernel leaf under a metadata syscall (stat family, access, open/openat/close, getdents64, readlink, getcwd, chdir, mkdir/unlink/rename, utimensat, chmod...), or a path-walk/dcache/readdir leaf",
  lambda k: k["kern"] and (k["sc"] in FS_META_SC or K_FSMETA.match(k["sym"]))),
 ("K12", "other kernel", "other kernel", "kernel", "any other kernel leaf (data read/write, pipes, signals, timers, interrupts/softirqs, networking...)",
  lambda k: k["kern"]),
 ("U11", "core logic", "python interpreter / extensions", "user", "remaining user leaf in a python process in the interpreter, an extension module, libm/BLAS/libstdc++ (the program's own work)",
  lambda k: PY_COMM.match(k["comm"]) and (PY_DSO.search(k["dso"]) or U_LIBC_STR.match(k["sym"]))),
 ("U12", "core logic", "compiler", "user", "remaining user leaf in a compiler/assembler/linker process (cc1, cc1plus, as, ld, collect2, lto1, clang)",
  lambda k: COMPILER_COMM.match(k["comm"])),
 ("U13", "core logic", "cli tool (git/grep/sed/...)", "user", "remaining user leaf in git, grep, rg, sed, cat, find, head/tail, wc, ls... (their own binary, libc string/regex routines, libpcre)",
  lambda k: TOOL_COMM.match(k["comm"]) and (not k["dso"].startswith("/usr/lib/x86_64-linux-gnu/libc") or U_LIBC_STR.match(k["sym"]))),
 ("U14", "other user-space", "shell / glue / misc libc", "user", "remaining user leaf in bash/sh/timeout/tee/env, the vDSO, or libc routines not covered above (stdio, getenv, qsort, strtol, locale...)",
  lambda k: True),
]

def categorize(group, comm, sym, dso, sc, ctx):
    k = {"group": group, "comm": comm, "sym": sym, "dso": dso, "sc": sc, "ctx": ctx, "kern": is_kernel(dso)}
    for rid, cat, sub, scope, desc, pred in RULES:
        if pred(k):
            return cat, sub, rid
    return "unclassified", "no rule", "-"

# Inclusive (stack-context) metrics, independent of the leaf category.
def inclusive_flags(sym, dso, sc, ctx):
    c = set(ctx.split("|")) if ctx else set()
    f = set()
    if c & {"import", "pystartup"}: f.add("under import/startup")
    if "pf" in c: f.add("under page fault")
    if sc in LIFE_SC or c & {"exec", "fork", "exit", "ldso", "pyfini"} or "pf" in c: f.add("lifecycle (incl. page faults, ld.so, teardown)")
    if sc in FS_META_SC: f.add("under fs-metadata syscall")
    if "pycompile" in c: f.add("under python compile")
    if "pyfini" in c: f.add("under python teardown")
    return f

def markdown():
    out = ["| Order | Rule | Category | Subcategory | Scope | Matches |", "|---|---|---|---|---|---|"]
    for i, (rid, cat, sub, scope, desc, _) in enumerate(RULES, 1):
        out.append(f"| {i} | {rid} | {cat} | {sub} | {scope} | {desc} |")
    return "\n".join(out)

if __name__ == "__main__":
    if "--markdown" in sys.argv: print(markdown())
