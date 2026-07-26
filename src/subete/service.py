"""Strictly sequential non-mutating FileTalk service slice."""
import time
from . import filetalk, request, state
from .requests import execute_request
from .setup import validate_database
from .recovery import recover_pending

def process_one():
    state.update_now()
    if not filetalk.discover_next_message():
        return False
    request.possess_current_message()
    request.claim_current_message()
    try:
        execute_request()
        filetalk.deliver_reply_back_to_sender()
        request.record_successful_completion()
    except (OSError, ValueError) as error:
        request.record_failure_to_complete(error)
    return True

def run_service():
    validate_database()
    recover_pending()
    try:
        while True:
            process_one(); time.sleep(.1)
    except KeyboardInterrupt: return
