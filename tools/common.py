"""Shared helpers: command classification and log loading."""
import json, re

CLASSES = ["search/read", "git", "package install", "test run", "build", "other"]

def _segments(cmd):
    """Split a shell command into simple commands (quote-aware; heredoc bodies dropped)."""
    import shlex
    body = re.sub(r"<<-?'?(\w+)'?\n.*?\n\1(\n|$)", "\n", cmd, flags=re.S)
    lex = shlex.shlex(body.replace("\n", " ; "), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    segs, cur = [], []
    try:
        for tok in lex:
            if tok and set(tok) <= set("|&;()"):
                if cur: segs.append(" ".join(cur)); cur = []
            elif tok and set(tok) <= set("<>") :
                cur.append(tok)
            else:
                cur.append(tok)
    except ValueError:
        return [s.strip() for s in re.split(r"&&|;|\n", body) if s.strip()]
    if cur: segs.append(" ".join(cur))
    return segs

def _verb(seg):
    toks = seg.split()
    while toks and (re.match(r"^\w+=", toks[0]) or toks[0] in ("sudo", "time", "env", "timeout", "nice")):
        toks = toks[1:]
    return toks

def classify(cmd):
    """Map a recorded shell command to a command class (precedence: package
    install > build > test run > ad-hoc python ('other') > git > search/read > other)."""
    segs = [_verb(s) for s in _segments(cmd)]
    flat = " ".join(" ".join(t) for t in segs)
    if re.search(r"\bpip3? (install|download|uninstall)\b|\buv pip\b|-m venv\b|\bvirtualenv\b|setup\.py (develop|install)", flat):
        return "package install"
    if re.search(r"setup\.py build|build_ext|\bmake\b|\bmeson\b|\bninja\b|\bcythonize\b|-m build\b|\bpython -m compileall", flat):
        return "build"
    if re.search(r"\bpytest\b|runtests\.py|bin/test\b|-m unittest\b|\btox\b|\bnox\b", flat):
        return "test run"
    verbs = [t[0].split("/")[-1] for t in segs if t]
    if any(re.match(r"^python(3(\.\d+)?)?$", v) for v in verbs):
        return "other"          # ad-hoc python (repro scripts, python -c checks) dominates CPU
    if "git" in verbs:
        return "git"
    readers = {"grep", "rg", "cat", "find", "sed", "head", "tail", "ls", "wc", "awk", "less", "tree", "nl", "sort", "uniq", "cut", "diff", "file", "stat", "echo", "cd", "pwd", "xargs", "true", "printf"}
    if verbs and all(v in readers for v in verbs):
        return "search/read"
    return "other"

def load_calls(path):
    return [json.loads(l) for l in open(path) if l.strip()]
