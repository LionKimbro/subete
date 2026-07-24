"""Strictly sequential non-mutating FileTalk service slice."""
import time
from . import fsio
from .filetalk import claim_message, complete_request, deliver_reply, discover_messages, fail_request
from .requests import execute_request
from .setup import validate_database
from .recovery import recover_pending

def process_one(now):
    messages = discover_messages(now)
    if not messages: return False
    candidate = messages[0]; claimed = claim_message(candidate["path"])
    try:
        message = candidate["message"]
        fsio.read_json("identity", ["required"])
        database_id = fsio.read["data"]["database-id"]
        response = execute_request(database_id, message)
        fsio.read_json("configuration", ["required"])
        deliver_reply(fsio.read["data"], message["reply"], response)
        complete_request(claimed, {"status": "success", "response": response})
    except (OSError, ValueError) as error:
        fail_request(claimed, {"status": "failure", "error": str(error)})
    return True

def run_service():
    validate_database()
    fsio.read_json("identity", ["required"])
    recover_pending(fsio.read["data"]["database-id"])
    try:
        while True:
            process_one(time.time()); time.sleep(.1)
    except KeyboardInterrupt: return
