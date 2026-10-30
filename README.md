# job-board

A tiny file-based job queue for splitting work across several workers (scripts, render boxes, or teammates).
A lead posts jobs into a folder; workers claim one atomically, write results, and mark it done or failed.
Optional HTTP API lets remote workers join with a per-worker bearer key.

- No database: each job is a JSON file that moves `queue/ → claimed/ → done/ | failed/`.
- Claims use `os.rename`, so two workers can never get the same job.
- Only the worker that claimed a job can upload to it or finish it.
- API: bearer keys, per-key and per-IP rate limits, upload type allow-list, 200 MB cap, path-traversal checks.

## Quick start (local)

    python3 jobboard/hb.py add --title "Render scene 01" --brief "Make out.mp4 from scene01.png"
    python3 jobboard/hb.py claim --bot worker-1
    python3 jobboard/hb.py done --id <ID> --bot worker-1 --summary "out.mp4, 5s" --files out.mp4
    python3 jobboard/hb.py list

Data lives in `./board` (override with `JOBBOARD_ROOT`).

## HTTP API (remote workers)

    pip install -r requirements.txt
    python3 jobboard/keys.py mint worker-1        # prints a key; stored in $JOBBOARD_ROOT/keys.json (0600)
    cd jobboard && uvicorn server:app --host 127.0.0.1 --port 8787

Put it behind your own HTTPS reverse proxy or tunnel before exposing it. Endpoints are documented in
[`jobboard/API.md`](jobboard/API.md) and served at `GET /`. Revoke with `keys.py revoke worker-1`.

## Examples

- `examples/render_job.sh` — full local flow
- `examples/remote_worker.sh` — claim, upload and finish over HTTP
- `examples/job.example.json` — job file format

## Tests

    pip install -r requirements.txt pytest httpx && pytest -q

## License

MIT
