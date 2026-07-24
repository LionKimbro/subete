"""Strictly sequential non-mutating FileTalk service slice."""
import time
from .filetalk import claim_message, complete_request, deliver_reply, discover_messages, fail_request
from .fsio import read_json
from .requests import execute_request
from .setup import validate_database
from .recovery import recover_pending

def process_one(now):
    messages = discover_messages(now)
    if not messages: return False
    candidate = messages[0]; claimed = claim_message(candidate["path"])
    try:
        message = candidate["message"]
        response = execute_request(read_json("identity")["database-id"], message)
        deliver_reply(read_json("configuration"), message["reply"], response)
        complete_request(claimed, {"status": "success", "response": response})
    except (OSError, ValueError) as error:
        fail_request(claimed, {"status": "failure", "error": str(error)})
    return True

def run_service():
    validate_database()
    recover_pending(read_json("identity")["database-id"])
    try:
        while True:
            process_one(time.time()); time.sleep(.1)
    except KeyboardInterrupt: return
