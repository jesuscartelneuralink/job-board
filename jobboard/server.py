import json, os, glob, re, time, datetime, threading
from collections import defaultdict, deque
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import PlainTextResponse
ROOT=os.environ.get("JOBBOARD_ROOT",os.path.abspath("board")); API=os.path.dirname(os.path.abspath(__file__)); KEYS=os.environ.get("JOBBOARD_KEYS",f"{ROOT}/keys.json"); NOTE=f"{ROOT}/notifications.log"
MAXB=200*1024*1024
EXT={"mp4","mov","png","jpg","jpeg","webp","wav","mp3","m4a","srt","vtt","txt","md","json"}
JID=re.compile(r"^[A-Za-z0-9._-]{1,80}$")
app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
lock=threading.Lock(); hits=defaultdict(deque)
def now(): return datetime.datetime.now().astimezone().isoformat(timespec="seconds")
def load(p): return json.load(open(p))
def save(p,d):
    t=p+".tmp"; json.dump(d,open(t,"w"),indent=2); os.replace(t,p)
def ratelimit(k,n=60,w=60):
    q=hits[k]; t=time.time()
    while q and q[0]<t-w: q.popleft()
    if len(q)>=n: raise HTTPException(429,"rate limited")
    q.append(t)
def auth(req):
    ip=req.client.host if req.client else "?"
    ratelimit("ip:"+ip,120)
    h=req.headers.get("authorization","")
    if not h.startswith("Bearer "): raise HTTPException(401,"missing bearer key")
    try: keys=load(KEYS)
    except Exception: keys={}
    lab=keys.get(h[7:].strip())
    if not lab: raise HTTPException(401,"bad key")
    ratelimit("key:"+lab,60); return lab
def find(jid):
    if not JID.match(jid): raise HTTPException(400,"bad id")
    for s in ("queue","claimed","done","failed"):
        p=f"{ROOT}/{s}/{jid}.json"
        if os.path.exists(p): return s,p
    raise HTTPException(404,"not found")
def bot_ok(b):
    if not b or not re.match(r"^[\w .@-]{1,60}$",b): raise HTTPException(400,"bad bot name")
    return b
def updir(d):
    o=os.path.realpath(d.get("output_dir") or "")
    if not o.startswith(ROOT+"/"): o=f"{ROOT}/results/{d['id']}"
    return o
def public(d,s):
    return {k:d.get(k) for k in ("id","title","brief","status","created","bot","claimed","finished","summary","reason","files","external","review_required")}|{"state":s}
def mine(d,s,lab,bot):
    if s!="claimed" or d.get("api_key_label")!=lab or d.get("bot")!=bot:
        raise HTTPException(403,"only the claiming bot (same key + bot name) may do this")
DOC=open(f"{API}/API.md").read
@app.get("/",response_class=PlainTextResponse)
def index(): return DOC()
@app.get("/jobs")
def jobs(req:Request):
    auth(req); out=[]
    for p in sorted(glob.glob(f"{ROOT}/queue/*.json"),key=os.path.getmtime):
        try: d=load(p); out.append({"id":d["id"],"title":d.get("title")})
        except Exception: pass
    return out
@app.post("/claim")
async def claim(req:Request):
    lab=auth(req); bot=bot_ok((await req.json()).get("bot"))
    for p in sorted(glob.glob(f"{ROOT}/queue/*.json"),key=os.path.getmtime):
        dst=p.replace("/queue/","/claimed/")
        try: os.rename(p,dst)
        except FileNotFoundError: continue
        d=load(dst); d.update(status="claimed",bot=bot,claimed=now(),external=True,review_required=True,
            api_key_label=lab,note="claimed by external bot via API; results need review",
            api_log=d.get("api_log",[])+[{"t":now(),"action":"claim","key":lab,"bot":bot}])
        save(dst,d); os.makedirs(updir(d),exist_ok=True); return public(d,"claimed")
    raise HTTPException(404,"NO_JOBS")
@app.get("/jobs/{jid}")
def show(jid:str,req:Request):
    auth(req); s,p=find(jid); return public(load(p),s)
@app.post("/jobs/{jid}/files")
async def upload(jid:str,req:Request,bot:str=Form(...),file:UploadFile=File(...)):
    lab=auth(req); bot=bot_ok(bot); s,p=find(jid); d=load(p); mine(d,s,lab,bot)
    name=re.sub(r"[^A-Za-z0-9._-]","_",os.path.basename(file.filename or ""))[:120].lstrip(".")
    if not name or name.rsplit(".",1)[-1].lower() not in EXT or "." not in name: raise HTTPException(400,"file type not allowed")
    od=updir(d); os.makedirs(od,exist_ok=True); dst=os.path.join(od,name)
    if os.path.dirname(os.path.realpath(dst))!=os.path.realpath(od): raise HTTPException(400,"bad name")
    n=0; tmp=dst+".part"
    with open(tmp,"wb") as f:
        while (c:=await file.read(1<<20)):
            n+=len(c)
            if n>MAXB: f.close(); os.remove(tmp); raise HTTPException(413,"file > 200MB")
            f.write(c)
    os.replace(tmp,dst)
    with lock:
        d=load(p); d["api_log"]=d.get("api_log",[])+[{"t":now(),"action":"upload","key":lab,"bot":bot,"file":name,"bytes":n}]
        d["files"]=sorted(set(d.get("files") or [])|{name}); save(p,d)
    return {"saved":name,"bytes":n}
async def finish(jid,req,tgt):
    lab=auth(req); b=await req.json(); bot=bot_ok(b.get("bot")); s,p=find(jid); d=load(p); mine(d,s,lab,bot)
    msg=str(b.get("summary" if tgt=="done" else "reason") or "")[:4000]
    d.update(status=tgt,finished=now(),**({"summary":msg} if tgt=="done" else {"reason":msg}))
    d["api_log"]=d.get("api_log",[])+[{"t":now(),"action":tgt,"key":lab,"bot":bot}]
    save(f"{ROOT}/{tgt}/{jid}.json",d); os.remove(p)
    with open(NOTE,"a") as f: f.write(json.dumps({"time":now(),"id":jid,"bot":bot,"key":lab,"status":tgt,"summary":msg})+"\n")
    return public(d,tgt)
@app.post("/jobs/{jid}/done")
async def done(jid:str,req:Request): return await finish(jid,req,"done")
@app.post("/jobs/{jid}/fail")
async def fail(jid:str,req:Request): return await finish(jid,req,"failed")
