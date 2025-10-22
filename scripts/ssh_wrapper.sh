#!/bin/bash
# /opt/ngs_webinterface/scripts/ssh_wrapper.sh - Optimiert

set -euo pipefail

# Configuration
REMOTE_USER="odin"
MUBAC_HOST="10.20.30.216"
SPECDIFF_HOST="10.20.30.217"
REMOTE_HOST="$MUBAC_HOST"  # Default host; can be changed based on analysis
KEY="/opt/ngs_webinterface/.ssh/.sshKey"
TIMEOUT=30
LOG_DIR="/var/log/ngs_webinterface"
MAX_RETRIES=3

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_DIR/ssh_wrapper.log"
}

# SSH command with timeout and error handling
ssh_cmd() {
    local retries=0
    local cmd="$*"
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if timeout $TIMEOUT ssh -i "$KEY" \
            -o StrictHostKeyChecking=no \
            -o ConnectTimeout=10 \
            -o ServerAliveInterval=60 \
            -o ServerAliveCountMax=3 \
            -o BatchMode=yes \
            "${REMOTE_USER}@${REMOTE_HOST}" "$cmd"; then
            return 0
        else
            retries=$((retries + 1))
            log "SSH command failed (attempt $retries/$MAX_RETRIES)"
            if [ $retries -lt $MAX_RETRIES ]; then
                sleep $((retries * 2))  # Exponential backoff
            fi
        fi
    done
    
    log "SSH command failed after $MAX_RETRIES attempts: $cmd"
    return 1
}

# Validate inputs
if [ $# -eq 0 ]; then
    echo "Error: No arguments provided" >&2
    log "Error: No arguments provided"
    exit 1
fi

MODE="$1"
shift

log "Starting SSH wrapper with mode: $MODE"


case "$MODE" in

    run)
        if [ $# -ne 4 ]; then
            echo "Error: run mode requires exactly 4 arguments" >&2
            log "Error: run mode requires exactly 4 arguments, got $#"
            exit 1
        fi
        
        ANALYSIS_TYPE="$1"
        INPUT_PATH="$2" 
        SAMPLES="$3"
        JOB_ID="$4"
        
        # Escape special characters in paths and samples
        ESCAPED_INPUT_PATH=$(printf '%q' "$INPUT_PATH")
        ESCAPED_SAMPLES=$(printf '%q' "$SAMPLES")
        ESCAPED_JOB_ID=$(printf '%q' "$JOB_ID")

        log "Starting analysis: type=$ANALYSIS_TYPE, path=$INPUT_PATH, job=$JOB_ID"

        # Validate analysis type
        case "$ANALYSIS_TYPE" in
            wgs)
            REMOTE_HOST="$MUBAC_HOST"
            ssh_cmd "nohup /bacteria/scripts/ngsInterface.sh '$ANALYSIS_TYPE' $ESCAPED_INPUT_PATH $ESCAPED_SAMPLES $ESCAPED_JOB_ID > /tmp/job_${JOB_ID}.log 2>&1 & echo \$! > /tmp/job_${JOB_ID}.pid"
            ;;
            
            species) 
            REMOTE_HOST="$SPECDIFF_HOST"
            ssh_cmd "nohup /animalSpecies/scripts/ngsInterface.sh '$ANALYSIS_TYPE' $ESCAPED_INPUT_PATH $ESCAPED_SAMPLES $ESCAPED_JOB_ID > /tmp/job_${JOB_ID}.log 2>&1 & echo \$! > /tmp/job_${JOB_ID}.pid"
            ;;

            *) 
                echo "Error: Invalid analysis type: $ANALYSIS_TYPE" >&2
                log "Error: Invalid analysis type: $ANALYSIS_TYPE"
                exit 1
                ;;
        esac
        log "Analysis started successfully for job: $JOB_ID"
        ;;

    get_log)
        if [ $# -ne 2 ]; then
            echo "Error: get_log mode requires exactly 2 arguments" >&2
            log "Error: get_log mode requires exactly 2 arguments, got $#"
            exit 1
        fi
        
        INPUT_PATH="$1"
        ANALYSIS_TYPE="$2"
        ESCAPED_INPUT_PATH=$(printf '%q' "$INPUT_PATH")
        LOG_FILE="$INPUT_PATH/logs/analysis.log"

        case "$ANALYSIS_TYPE" in
            wgs)
            REMOTE_HOST="$MUBAC_HOST"
            ;;
            
            species) 
            REMOTE_HOST="$SPECDIFF_HOST"
            ;;

            *)
            ;;
        esac
        
        log "Fetching log from: $LOG_FILE"
        
        # Try multiple possible log locations
        ssh_cmd "
            if [ -f '$LOG_FILE' ]; then
                tail -n 1000 '$LOG_FILE'
            elif [ -f '$INPUT_PATH/analysis.log' ]; then
                tail -n 1000 '$INPUT_PATH/analysis.log'
            else
                echo '[INFO] Logfile noch nicht verfügbar'
            fi
        "
        ;;

    kill)
        if [ $# -ne 2 ]; then
            echo "Error: kill mode requires exactly 2 arguments" >&2
            log "Error: kill mode requires exactly 2 arguments, got $#"
            exit 1
        fi
        
        JOB_ID="$1"
        ANALYSIS_TYPE="$2"
        PID_FILE="/tmp/job_${JOB_ID}.pid"

        case "$ANALYSIS_TYPE" in
            wgs)
            REMOTE_HOST="$MUBAC_HOST"
            ;;
            
            species) 
            REMOTE_HOST="$SPECDIFF_HOST"
            ;;

            *)
            ;;
        esac
        
        log "Attempting to kill job: $JOB_ID"
        
        ssh_cmd "
            if [ -f '$PID_FILE' ]; then
                PID=\$(cat '$PID_FILE')
                if kill -0 \$PID 2>/dev/null; then
                    kill -TERM \$PID
                    sleep 5
                    if kill -0 \$PID 2>/dev/null; then
                        kill -KILL \$PID
                    fi
                    rm -f '$PID_FILE'
                    echo 'Process killed successfully'
                else
                    rm -f '$PID_FILE'
                    echo 'Process was already dead'
                fi
            else
                # Try to kill by job name pattern
                pkill -f 'ngsInterface.sh.*$JOB_ID' || echo 'No matching processes found'
            fi
        "
        ;;

    status)
    REMOTE_HOST="$SPECDIFF_HOST"  # or MUBAC_HOST
        if [ $# -ne 1 ]; then
            echo "Error: status mode requires exactly 1 argument" >&2
            log "Error: status mode requires exactly 1 argument, got $#"
            exit 1
        fi
        
        JOB_ID="$1"
        PID_FILE="/tmp/job_${JOB_ID}.pid"
        
        ssh_cmd "
            if [ -f '$PID_FILE' ]; then
                PID=\$(cat '$PID_FILE')
                if kill -0 \$PID 2>/dev/null; then
                    echo 'running'
                else
                    echo 'finished'
                fi
            else
                echo 'not_found'
            fi
        "
        ;;

    test)
        REMOTE_HOST="$SPECDIFF_HOST"  # or MUBAC_HOST
        log "Testing SSH connection"
        ssh_cmd "echo 'SSH connection successful' && hostname && date"
        ;;

    *)
        echo "Error: Invalid mode: $MODE" >&2
        echo "Valid modes: run, get_log, kill, status, test" >&2
        log "Error: Invalid mode: $MODE"
        exit 1
        ;;
esac

log "SSH wrapper completed successfully for mode: $MODE"