#!/usr/bin/env python3
"""Manage helper API keys. Usage: keys.py mint LABEL [--file PATH] | revoke LABEL | list"""
import json, os, secrets, sys
K = os.environ.get("JOBBOARD_KEYS", os.path.join(os.environ.get("JOBBOARD_ROOT", os.path.abspath("board")), "keys.json"))
def load(): return json.load(open(K)) if os.path.exists(K) else {}
def save(d):
    os.makedirs(os.path.dirname(K), exist_ok=True)
    t = K+".tmp"; fd = os.open(t, os.O_WRONLY|os.O_CREAT|os.O_TRUNC, 0o600)
    with os.fdopen(fd,"w") as f: json.dump(d,f,indent=2)
    os.replace(t,K); os.chmod(K,0o600)
c = sys.argv[1:]
if not c: sys.exit(__doc__)
d = load()
if c[0]=="mint":
    lab=c[1]; key="hb_"+secrets.token_urlsafe(32)
    d={k:v for k,v in d.items() if v!=lab}; d[key]=lab; save(d)
    if "--file" in c:
        p=c[c.index("--file")+1]; fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,"w") as f: f.write(key+"\n")
        os.chmod(p,0o600); print(f"minted {lab} -> {p}")
    else: print(key)
elif c[0]=="revoke":
    n={k:v for k,v in d.items() if v!=c[1]}; save(n); print(f"revoked {len(d)-len(n)} key(s) for {c[1]}")
elif c[0]=="list":
    for v in sorted(set(d.values())): print(v)
