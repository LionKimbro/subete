"""Strictly sequential non-mutating FileTalk service slice."""
import time
from .filetalk import claim_message, complete_request, deliver_reply, discover_messages, fail_request
from .fsio import read_json_file
from .paths import g
from .requests import execute_request
from .setup import validate_existing_database
from .recovery import recover_pending

def process_one(paths, now):
    messages = discover_messages(paths, now)
    if not messages: return False
    candidate = messages[0]; claimed = claim_message(paths, candidate["path"])
    try:
        message = candidate["message"]
        response = execute_request(paths, read_json_file(paths["identity"])["database-id"], message)
        deliver_reply(paths, read_json_file(paths["configuration"]), message["reply"], response)
        complete_request(paths, claimed, {"status": "success", "response": response})
    except (OSError, ValueError) as error:
        fail_request(paths, claimed, {"status": "failure", "error": str(error)})
    return True

def run_service():
    validate_existing_database()
    recover_pending(g, read_json_file(g["identity"])["database-id"])
    try:
        while True:
            process_one(g, time.time()); time.sleep(.1)
    except KeyboardInterrupt: return
