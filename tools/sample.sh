#!/usr/bin/env bash
# sample.sh — background sampler of /proc/stat and /proc/meminfo every 200 ms.
# Uses only bash builtins inside the loop (no fork per sample).
# usage: tools/sample.sh <out.csv> [interval_us=200000] &
out=$1; iv=${2:-200000}
exec {sfd}<> <(:)          # never-readable fd: `read -t` on it is a fork-free sleep
echo "ts_us,user,nice,system,idle,iowait,irq,softirq,steal,ctxt,procs_running,procs_blocked,mem_total_kb,mem_free_kb,mem_avail_kb,cached_kb,dirty_kb" > "$out"
next=${EPOCHREALTIME/./}
while :; do
  ts=${EPOCHREALTIME/./}
  while read -r k a b c d e f g h rest; do
    case $k in
      cpu) cu=$a cn=$b cs=$c ci=$d cw=$e cq=$f csq=$g cst=$h;;
      ctxt) ctxt=$a;; procs_running) pr=$a;; procs_blocked) pb=$a;;
    esac
  done < /proc/stat
  while read -r k v u; do
    case $k in
      MemTotal:) mt=$v;; MemFree:) mf=$v;; MemAvailable:) ma=$v;; Cached:) mc=$v;; Dirty:) md=$v;;
    esac
  done < /proc/meminfo
  echo "$ts,$cu,$cn,$cs,$ci,$cw,$cq,$csq,$cst,$ctxt,$pr,$pb,$mt,$mf,$ma,$mc,$md" >> "$out"
  next=$(( next + iv )); now=${EPOCHREALTIME/./}; rem=$(( next - now ))
  if (( rem > 0 )); then read -t "$(printf '%d.%06d' $((rem/1000000)) $((rem%1000000)))" -u $sfd _; else next=$now; fi
done
