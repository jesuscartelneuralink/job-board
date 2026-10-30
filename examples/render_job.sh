#!/bin/bash
# Post a job, claim it as a worker, finish it. Runs against ./board.
set -e
J=$(python3 jobboard/hb.py add --title "Render scene 01" --brief "Make a 9:16 5s clip from scene01.png; save as out.mp4")
python3 jobboard/hb.py claim --bot worker-1
python3 jobboard/hb.py done --id "$J" --bot worker-1 --summary "out.mp4, 5s" --files out.mp4
python3 jobboard/hb.py list
