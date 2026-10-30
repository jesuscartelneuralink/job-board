#!/usr/bin/env python3
"""Helper-bot job board. Folder set by JOBBOARD_ROOT (default ./board).
Usage:
  hb.py add --title T --brief "..." [--out DIR] [--id ID]   (lead bot posts a job)
  hb.py list [queue|claimed|done|failed]
  hb.py claim --bot NAME            (atomically claims oldest queued job, prints it as JSON)
  hb.py done --id ID --bot NAME --summary "..." [--files f1 f2]
  hb.py fail --id ID --bot NAME --reason "..."
  hb.py show --id ID
"""
import argparse, json, os, sys, time, glob, datetime
ROOT = os.environ.get("JOBBOARD_ROOT", os.path.abspath("board"))
for _s in ("queue","claimed","done","failed","results"): os.makedirs(f"{ROOT}/{_s}", exist_ok=True)
def now(): return datetime.datetime.now().astimezone().isoformat(timespec="seconds")
def path(state, jid): return f"{ROOT}/{state}/{jid}.json"
def load(p): return json.load(open(p))
def save(p, d):
    tmp = p + ".tmp"; json.dump(d, open(tmp, "w"), indent=2); os.replace(tmp, p)
def find(jid):
    for s in ("queue","claimed","done","failed"):
        if os.path.exists(path(s,jid)): return s, path(s,jid)
    sys.exit(f"job {jid} not found")
a = argparse.ArgumentParser(); a.add_argument("cmd")
a.add_argument("state", nargs="?"); a.add_argument("--title"); a.add_argument("--brief")
a.add_argument("--out"); a.add_argument("--id"); a.add_argument("--bot")
a.add_argument("--summary"); a.add_argument("--reason"); a.add_argument("--files", nargs="*", default=[])
x = a.parse_args()
if x.cmd == "add":
    jid = x.id or time.strftime("J%Y%m%d-%H%M%S")
    out = x.out or f"{ROOT}/results/{jid}"
    save(path("queue",jid), {"id":jid,"title":x.title,"brief":x.brief,"output_dir":out,
        "status":"queued","created":now(),"report_to":os.environ.get("JOBBOARD_OWNER","lead")})
    print(jid)
elif x.cmd == "list":
    for s in ([x.state] if x.state else ["queue","claimed","done","failed"]):
        for p in sorted(glob.glob(f"{ROOT}/{s}/*.json")):
            d = load(p); print(f"{s:8} {d['id']}  {d.get('title','')}  {d.get('bot','')}")
elif x.cmd == "claim":
    if not x.bot: sys.exit("--bot required")
    for p in sorted(glob.glob(f"{ROOT}/queue/*.json"), key=os.path.getmtime):
        dst = p.replace("/queue/","/claimed/")
        try: os.rename(p, dst)   # atomic: only one bot wins
        except FileNotFoundError: continue
        d = load(dst); d.update(status="claimed", bot=x.bot, claimed=now()); save(dst, d)
        os.makedirs(d["output_dir"], exist_ok=True); print(json.dumps(d, indent=2)); sys.exit(0)
    print("NO_JOBS"); sys.exit(3)
elif x.cmd in ("done","fail"):
    s, p = find(x.id); d = load(p)
    if s != "claimed" or d.get("bot") != x.bot: sys.exit(f"job is {s}, claimed by {d.get('bot')}")
    tgt = "done" if x.cmd=="done" else "failed"
    d.update(status=tgt, finished=now(), summary=x.summary, reason=x.reason, files=x.files)
    save(path(tgt,x.id), d); os.remove(p); print(json.dumps(d, indent=2))
elif x.cmd == "show":
    print(json.dumps(load(find(x.id)[1]), indent=2))
