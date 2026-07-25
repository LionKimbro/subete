"""Strictly sequential non-mutating FileTalk service slice."""
import time
from . import filetalk, state
from .requests import execute_request
from .setup import validate_database
from .recovery import recover_pending

def process_one():
    state.update_now()
    if not filetalk.discover_next_message(): return False
    filetalk.claim_message()
    try:
        message = filetalk.current["message"]
        response = execute_request(state.g["database-id"], message)
        filetalk.deliver_reply(response)
        filetalk.complete_request({"status": "success", "response": response})
    except (OSError, ValueError) as error:
        filetalk.fail_request({"status": "failure", "error": str(error)})
    return True

def run_service():
    validate_database()
    recover_pending(state.g["database-id"])
    try:
        while True:
            process_one(); time.sleep(.1)
    except KeyboardInterrupt: return
