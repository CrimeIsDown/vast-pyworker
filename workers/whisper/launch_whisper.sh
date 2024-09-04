#!/bin/bash
set -e

start_server() {
    if [ ! -d "$1" ]
    then
        wget -O - https://raw.githubusercontent.com/CrimeIsDown/vast-pyworker/whisper/start_server.sh | bash
    else
        $1/start_server.sh
    fi
}

export WORKSPACE_DIR="/workspace"
export BACKEND="whisper"
export MODEL_LOG="$WORKSPACE_DIR/infer.log"
export HF_TOKEN="changeme"
start_server "$WORKSPACE_DIR/vast-pyworker"

export ASR_MODEL_PATH="$(realpath ~/.cache/whisper)"
echo "saving model to $ASR_MODEL_PATH"
cd /app
if [ ! -d "$ASR_MODEL_PATH" ]
then
    echo "starting model download" > $MODEL_LOG
    poetry run app/download_model.py > $WORKSPACE_DIR/download.log 2>&1
fi
poetry run gunicorn --bind 0.0.0.0:9000 --workers 1 --timeout 0 app.webservice:app -k uvicorn.workers.UvicornWorker >> $MODEL_LOG 2>&1 &
echo "done"
