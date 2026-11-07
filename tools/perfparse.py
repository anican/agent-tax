"""perfparse.py — reduce `perf script --show-task-events` output of a system-wide
cpu-clock -g recording into compact aggregate counts.

usage: perf script ... | python perfparse.py <root_pid> <out.json>

Each sample is assigned to a group:
  cmd     — the replayed command's process tree (descendants of root_pid,
            tracked through PERF_RECORD_FORK events)
  kthread — kernel threads (comm matches kworker/ksoftirqd/rcu/... or pid 2's children)
  idle    — pid 0 (swapper / idle loop)
  other   — anything else (the Claude Code harness, perf itself, the sampler...)
For cmd and kthread samples it records a key:
  (group, comm, leaf_sym, leaf_dso, syscall, ctx) -> count
where syscall is the innermost __x64_sys_* / __ia32_sys_* frame name (or ""),
and ctx is a '|'-joined set of context flags derived from the whole stack
(see FLAGS below). Categories are assigned later by taxonomy.py so the
mapping can change without re-recording.
"""
import json, re, sys
from collections import Counter

KTHREAD_RE = re.compile(r'^(kworker|ksoftirqd|rcu_|migration|kswapd|jbd2|khugepaged|kcompactd|kthreadd|cpuhp|idle_inject|watchdog|kauditd|oom_reaper|writeback|kblockd|ext4|kintegrity|irq/|card|scsi|kdevtmpfs|khungtaskd|ksmd|kstrp|zswap|hwrng|pool_workqueue)')
SYSCALL_RE = re.compile(r'^(?:__x64_sys_|__ia32_sys_|__do_sys_|__se_sys_)(\w+)')

IMPORT_SYMS = ('PyImport_', '_PyImport_', 'import_find_and_load', '_imp_', 'import_name', 'builtin___import__')
STARTUP_SYMS = ('pymain_init', 'Py_InitializeFromConfig', 'pyinit_main', 'init_interp_main', 'pyinit_core',
                'Py_InitializeEx', '_Py_InitializeMain', 'pycore_interp_init', 'init_importlib')
PYFINI_SYMS = ('Py_FinalizeEx', 'finalize_modules', '_PyImport_Fini', 'Py_Exit', 'pymain_free')
COMPILE_SYMS = ('_PyAST_Compile', 'Py_CompileString', 'builtin_compile', '_PyPegen_run_parser', 'compiler_', '_PyParser_')
PF_SYMS = ('exc_page_fault', 'asm_exc_page_fault', 'handle_mm_fault')
IRQ_SYMS = ('asm_sysvec_', 'asm_common_interrupt', 'sysvec_', 'handle_softirqs', '__irq_exit_rcu', 'irq_exit_rcu', 'do_softirq')

def flags_for(stack):
    f = set(); sc = ""
    for sym, dso in stack:              # leaf first
        if not sc:
            m = SYSCALL_RE.match(sym)
            if m: sc = m.group(1)
        if sym.startswith(PF_SYMS): f.add('pf')
        elif sym.startswith(IRQ_SYMS): f.add('irq')
        elif sym.startswith(IMPORT_SYMS): f.add('import')
        elif sym.startswith(STARTUP_SYMS): f.add('pystartup')
        elif sym.startswith(PYFINI_SYMS): f.add('pyfini')
        elif sym.startswith(COMPILE_SYMS): f.add('pycompile')
        if 'ld-linux' in dso or sym.startswith(('_dl_', 'dl_main', '_dl_start')): f.add('ldso')
        if sym in ('load_elf_binary', 'bprm_execve', 'begin_new_exec'): f.add('exec')
        if sym in ('copy_process', 'kernel_clone', 'dup_mm'): f.add('fork')
        if sym in ('do_exit', 'do_group_exit', 'exit_mmap', 'mmput'): f.add('exit')
    return sc, '|'.join(sorted(f))

def main():
    root = int(sys.argv[1]); out = sys.argv[2]
    tree = {root}; kthreads = {2}
    counts = Counter(); groups = Counter(); comm_counts = Counter()
    hdr = None; stack = []
    fork_re = re.compile(r'PERF_RECORD_FORK\((\d+):(\d+)\):\((\d+):(\d+)\)')
    comm_re = re.compile(r'PERF_RECORD_COMM(?: exec)?: (.*):(\d+)/(\d+)')
    comm_of = {}
    def flush():
        if hdr is None: return
        comm, pid = hdr
        if pid == 0: g = 'idle'
        elif pid in tree: g = 'cmd'
        elif pid in kthreads or KTHREAD_RE.match(comm): g = 'kthread'
        else: g = 'other'
        groups[g] += 1
        if g in ('cmd', 'kthread'):
            leaf_sym, leaf_dso = stack[0] if stack else ('[unknown]', '[unknown]')
            sc, ctx = flags_for(stack)
            counts[(g, comm, leaf_sym, leaf_dso, sc, ctx)] += 1
            if g == 'cmd': comm_counts[comm] += 1
    for line in sys.stdin:
        if not line.strip():
            flush(); hdr = None; stack = []; continue
        if line[0] == '\t':
            if hdr is not None:
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    rest = parts[1]
                    i = rest.rfind(' (')
                    sym, dso = (rest[:i], rest[i+2:-1]) if i >= 0 else (rest, '')
                    sym = re.sub(r'\+0x[0-9a-f]+$', '', sym)
                    stack.append((sym, dso))
            continue
        flush(); hdr = None; stack = []
        if 'PERF_RECORD_' in line:
            mc = comm_re.search(line)
            if mc: comm_of[int(mc.group(2))] = mc.group(1)
            m = fork_re.search(line)
            if m:
                cpid, ctid, ppid, ptid = map(int, m.groups())
                if cpid != ppid and ppid in comm_of: comm_of.setdefault(cpid, comm_of[ppid])
                if ppid in tree: tree.add(cpid)
                if ppid in kthreads or ppid == 2: kthreads.add(cpid)
            continue
        m = re.match(r'^\s*(.+?)\s+(\d+)/(\d+)\s+\[\d+\]', line)
        if m:
            c, p = m.group(1).strip(), int(m.group(2))
            if c.startswith(':'): c = comm_of.get(p, c)
            hdr = (c, p)
    flush()
    json.dump({'root_pid': root, 'tree_pids': len(tree), 'groups': groups, 'comm': comm_counts,
               'samples': [list(k) + [v] for k, v in counts.most_common()]}, open(out, 'w'))

if __name__ == '__main__':
    main()
