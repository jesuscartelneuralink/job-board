import json, os, subprocess, sys, tempfile, pathlib
HB = str(pathlib.Path(__file__).resolve().parents[1] / "jobboard" / "hb.py")
def run(root, *a):
    return subprocess.run([sys.executable, HB, *a], capture_output=True, text=True, env={**os.environ, "JOBBOARD_ROOT": root})
def test_flow():
    with tempfile.TemporaryDirectory() as r:
        jid = run(r, "add", "--title", "t", "--brief", "b").stdout.strip()
        c = run(r, "claim", "--bot", "w1"); assert json.loads(c.stdout)["bot"] == "w1"
        assert run(r, "claim", "--bot", "w2").returncode == 3
        assert run(r, "done", "--id", jid, "--bot", "w2", "--summary", "x").returncode != 0
        assert run(r, "done", "--id", jid, "--bot", "w1", "--summary", "ok").returncode == 0
        assert os.path.exists(f"{r}/done/{jid}.json")
def test_api():
    from fastapi.testclient import TestClient
    with tempfile.TemporaryDirectory() as r:
        os.environ["JOBBOARD_ROOT"] = r
        sys.path.insert(0, str(pathlib.Path(HB).parent)); import importlib, server; importlib.reload(server)
        json.dump({"hb_test": "w"}, open(f"{r}/keys.json", "w"))
        jid = run(r, "add", "--title", "t", "--brief", "b").stdout.strip()
        c = TestClient(server.app); h = {"Authorization": "Bearer hb_test"}
        assert c.get("/jobs").status_code == 401
        assert c.post("/claim", json={"bot": "w"}, headers=h).json()["id"] == jid
        assert c.post(f"/jobs/{jid}/files", data={"bot": "w"}, files={"file": ("a.exe", b"x")}, headers=h).status_code == 400
        assert c.post(f"/jobs/{jid}/files", data={"bot": "w"}, files={"file": ("a.txt", b"x")}, headers=h).status_code == 200
        assert c.post(f"/jobs/{jid}/done", json={"bot": "w", "summary": "ok"}, headers=h).json()["state"] == "done"
