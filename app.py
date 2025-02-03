from flask import Flask, request, render_template, jsonify
import re
import os

app = Flask(__name__, static_url_path='/logs/static', static_folder='static', template_folder='templates')

LOG_FILE = "/var/log/freeswitch/freeswitch.log"

def get_last_call_id(dialed_number):
    """Finds the most recent Call-ID associated with a dialed number, handling encoding issues."""
    if not os.path.exists(LOG_FILE):
        return None

    last_call_id = None
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as log:
            for line in log:
                if dialed_number in line:
                    call_id_match = re.search(r'([a-f0-9\-]{36})', line)
                    if call_id_match:
                        last_call_id = call_id_match.group(1)  # Get the last occurrence
    except UnicodeDecodeError:
        with open(LOG_FILE, "r", encoding="iso-8859-1", errors="replace") as log:  # Fallback encoding
            for line in log:
                if dialed_number in line:
                    call_id_match = re.search(r'([a-f0-9\-]{36})', line)
                    if call_id_match:
                        last_call_id = call_id_match.group(1)  
    return last_call_id

def interpret_hangup_reason(reason):
    """Provides a human-readable explanation for the hangup reason."""
    explanations = {
        "NORMAL_CLEARING": "The call ended normally.",
        "NO_ANSWER": "The call was not answered.",
        "USER_BUSY": "The callee was busy.",
        "CALL_REJECTED": "The call was rejected by the callee.",
        "ORIGINATOR_CANCEL": "The caller canceled the call before it was answered.",
        "NETWORK_OUT_OF_ORDER": "Network connectivity issues caused the call to drop.",
        "CS_EXECUTE": "The call was terminated while executing a dialplan action (e.g., IVR, script, or early termination).",
        "DESTINATION_OUT_OF_ORDER": "Call failed - Destination number is out of service or unreachable.",
        "WRONG_CALL_STATE": "Call failed due to an invalid call state."
    }
    return explanations.get(reason, "Unknown reason - check logs for more details.")

def process_call_flow_line(line, call_flow):
    """Processes each call log line to determine call routing events."""
    destination_match = re.search(r'Transfer .*? to XML\[(\d+)@', line)
    if destination_match:
        destination = int(destination_match.group(1))
        event_description = "Call Routed"
        if 800 <= destination <= 899:
            event_description = "Time Condition Applied"
        elif 400 <= destination <= 499:
            event_description = "Call Sent to Ring Group"
        elif 200 <= destination <= 399:
            event_description = "Call Routed to an Extension"
        elif 600 <= destination <= 699:
            event_description = "Call Passed Through an IVR"
        call_flow.append({
            "event": event_description,
            "destination": destination,
            "log": line.strip()
        })

def find_hangup_details(call_id):
    """Finds the first hangup occurrence and determines who ended the call."""
    if not os.path.exists(LOG_FILE):
        return None, None, None

    first_hangup = None
    hangup_party = None
    hangup_reason = None
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as log:
            for line in log:
                if call_id in line and "hanging up" in line:
                    hangup_match = re.search(r'Channel (sofia/\S+) hanging up, cause: (\S+)', line)
                    if hangup_match:
                        first_hangup = hangup_match.group(1)  # First detected hangup party
                        hangup_party = hangup_match.group(1)
                        hangup_reason = hangup_match.group(2)
                        break  # Get the first occurrence
    except UnicodeDecodeError:
        with open(LOG_FILE, "r", encoding="iso-8859-1", errors="replace") as log:
            for line in log:
                if call_id in line and "hanging up" in line:
                    hangup_match = re.search(r'Channel (sofia/\S+) hanging up, cause: (\S+)', line)
                    if hangup_match:
                        first_hangup = hangup_match.group(1)  # First detected hangup party
                        hangup_party = hangup_match.group(1)
                        hangup_reason = hangup_match.group(2)
                        break  # Get the first occurrence

    return first_hangup, hangup_party, hangup_reason

def parse_call_flow(call_id, dialed_number):
    """Extracts call flow details using the most recent Call-ID, handling encoding errors and avoiding duplicates."""
    if not os.path.exists(LOG_FILE):
        return []

    call_flow = []
    seen_logs = set()  # To track duplicates
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as log:
            for line in log:
                if call_id in line and line not in seen_logs:
                    seen_logs.add(line)  # Avoid duplicates
                    process_call_flow_line(line, call_flow)
    except UnicodeDecodeError:
        with open(LOG_FILE, "r", encoding="iso-8859-1", errors="replace") as log:  # Fallback encoding
            for line in log:
                if call_id in line and line not in seen_logs:
                    seen_logs.add(line)  # Avoid duplicates
                    process_call_flow_line(line, call_flow)
    
    first_hangup, hangup_party, hangup_reason = find_hangup_details(call_id)
    detailed_reason = interpret_hangup_reason(hangup_reason) if hangup_reason else ""
    
    if hangup_reason:
        who_ended = "Callee Disconnected First" if dialed_number in hangup_party else "Caller Disconnected First"
        call_flow.append({
            "event": "Call Ended",
            "party": hangup_party,
            "reason": hangup_reason,
            "detailed_reason": detailed_reason,
            "who_ended": who_ended,
            "log": f"{who_ended} - Hangup by {hangup_party} due to {hangup_reason} ({detailed_reason})"
        })
    
    return call_flow

@app.route('/logs/', methods=['GET', 'POST'])
def index():
    flow = []
    number = ""
    if request.method == 'POST':
        number = request.form.get('number')
        if number:
            call_id = get_last_call_id(number)
            if call_id:
                flow = parse_call_flow(call_id, number)
    return render_template('index.html', number=number, flow=flow)




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)




