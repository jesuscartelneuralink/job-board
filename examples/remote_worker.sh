#!/bin/bash
# A remote worker using the HTTP API. Set BASE, KEY (from keys.py mint), BOT.
set -e
: "${BASE:?}" "${KEY:?}" "${BOT:=worker-remote}"
JOB=$(curl -sf -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d "{\"bot\":\"$BOT\"}" "$BASE/claim")
ID=$(echo "$JOB" | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])')
echo "claimed $ID"; echo "result for $ID" > result.txt
curl -sf -H "Authorization: Bearer $KEY" -F bot=$BOT -F file=@result.txt "$BASE/jobs/$ID/files"
curl -sf -X POST -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d "{\"bot\":\"$BOT\",\"summary\":\"result.txt\"}" "$BASE/jobs/$ID/done"
