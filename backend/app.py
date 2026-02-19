"""
Flask API server for the CI/CD Healing Agent.
Supports Server-Sent Events (SSE) for real-time frontend updates.
"""

import json
import os
import queue
import threading
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

# Load .env so GITHUB_TOKEN and other vars are available to all modules
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from agent.pipeline import run_pipeline

app = Flask(__name__)
CORS(app)

# ═══════════════════════════════════════════════════════════════════
#  IN-MEMORY STATE
# ═══════════════════════════════════════════════════════════════════

current_run = {
    "status": "idle",
    "message": "",
    "result": None,
}
run_lock = threading.Lock()

# All connected SSE clients get events pushed to their queues
sse_clients = []
sse_clients_lock = threading.Lock()


def broadcast_event(event_type: str, data: dict):
    """Push an SSE event to ALL connected clients."""
    event_data = json.dumps({"type": event_type, **data}, default=str)
    with sse_clients_lock:
        dead = []
        for q in sse_clients:
            try:
                q.put_nowait(event_data)
            except Exception:
                dead.append(q)
        for q in dead:
            sse_clients.remove(q)


# ═══════════════════════════════════════════════════════════════════
#  BACKGROUND PIPELINE RUNNER
# ═══════════════════════════════════════════════════════════════════

def run_agent_background(repo_url, team_name, leader_name):
    """Run the pipeline in a background thread, streaming events via SSE."""
    global current_run

    def status_callback(msg):
        with run_lock:
            current_run["message"] = msg

    def event_callback(event_type, data):
        """Called by pipeline.py to emit real-time events."""
        broadcast_event(event_type, data)

    try:
        with run_lock:
            current_run["status"] = "running"
            current_run["message"] = "Starting pipeline..."
            current_run["result"] = None

        broadcast_event("status", {"message": "Pipeline started"})

        result = run_pipeline(
            repo_url, team_name, leader_name,
            status_callback=status_callback,
            event_callback=event_callback,
        )

        with run_lock:
            current_run["status"] = "done"
            current_run["result"] = result
            current_run["message"] = "Pipeline completed"

    except Exception as e:
        with run_lock:
            current_run["status"] = "error"
            current_run["message"] = str(e)
            current_run["result"] = {"error": str(e), "final_status": "ERROR"}

        broadcast_event("error", {"message": str(e)})


# ═══════════════════════════════════════════════════════════════════
#  API ROUTES
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/run", methods=["POST"])
def start_run():
    """Start the agent pipeline."""
    global current_run

    with run_lock:
        if current_run["status"] == "running":
            return jsonify({"error": "Agent is already running"}), 409

    data = request.get_json()
    repo_url = data.get("repo_url", "").strip()
    team_name = data.get("team_name", "").strip()
    leader_name = data.get("leader_name", "").strip()

    if not repo_url:
        return jsonify({"error": "repo_url is required"}), 400
    if not team_name:
        return jsonify({"error": "team_name is required"}), 400
    if not leader_name:
        return jsonify({"error": "leader_name is required"}), 400

    # Start pipeline in background thread
    thread = threading.Thread(
        target=run_agent_background,
        args=(repo_url, team_name, leader_name),
        daemon=True,
    )
    thread.start()

    return jsonify({"message": "Agent started", "status": "running"}), 202


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get the current run status (legacy polling endpoint)."""
    with run_lock:
        return jsonify({
            "status": current_run["status"],
            "message": current_run["message"],
            "result": current_run["result"],
        })


@app.route("/api/events", methods=["GET"])
def sse_stream():
    """
    Server-Sent Events endpoint.
    The frontend connects here with EventSource to get real-time pipeline updates.
    Each event is a JSON object with a "type" field indicating the event kind.
    """
    def event_stream():
        q = queue.Queue()
        with sse_clients_lock:
            sse_clients.append(q)

        try:
            while True:
                try:
                    # Block with timeout so we can detect disconnects
                    data = q.get(timeout=30)
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    # Send a keep-alive comment to prevent connection timeout
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            with sse_clients_lock:
                if q in sse_clients:
                    sse_clients.remove(q)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/results", methods=["GET"])
def get_results():
    """Serve the latest results.json file."""
    results_path = os.path.join(os.path.dirname(__file__), "workspace", "results.json")
    if os.path.exists(results_path):
        with open(results_path, "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="application/json")
    return jsonify({"error": "No results available yet"}), 404


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # use_reloader=False prevents Flask from restarting when files in
    # workspace/ change during pipeline execution (clone, fix, etc.)
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True, use_reloader=False)
