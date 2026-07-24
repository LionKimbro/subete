"""Strictly sequential non-mutating FileTalk service slice."""
import time
from . import state
from .filetalk import (
    archive_completed_request,
    archive_failed_request,
    claim_inbox_message,
    deliver_reply,
    discover_messages,
)
from .requests import execute_request
from .setup import validate_database
from .recovery import recover_pending

def process_one():
    state.update_now()
    messages = discover_messages()
    if not messages: return False
    candidate = messages[0]; claimed = claim_inbox_message(candidate["path"])
    try:
        message = candidate["message"]
        response = execute_request(state.g["database-id"], message)
        deliver_reply(message["reply"], response)
        archive_completed_request(claimed, {"status": "success", "response": response})
    except (OSError, ValueError) as error:
        archive_failed_request(claimed, {"status": "failure", "error": str(error)})
    return True

def run_service():
    validate_database()
    recover_pending(state.g["database-id"])
    try:
        while True:
            process_one(); time.sleep(.1)
    except KeyboardInterrupt: return
