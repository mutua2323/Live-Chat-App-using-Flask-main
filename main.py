from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, send, join_room, leave_room
import random
import string

# Initialize Flask app
app = Flask(__name__)

# Configure Flask secret key
app.config["SECRET_KEY"] = "qwertymnbvcxz"

# Initialize SocketIO for real-time communication
socketio = SocketIO(app)

# Store active chat rooms and their messages
rooms = {}


def generate_unique_code(length: int) -> str:
    """Generate a unique uppercase code for each chat room."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase, k=length))
        if code not in rooms:
            return code


@app.route("/", methods=["GET", "POST"])
def home():
    """Home page for creating or joining chat rooms."""
    session.clear()

    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        create = request.form.get("create", False)
        join = request.form.get("join", False)

        # Validate name input
        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        # Validate join request
        if join and not code:
            return render_template("home.html", error="Please enter a room code.", name=name)

        room = code
        if create:  # Create a new chat room
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:  # Room doesn’t exist
            return render_template("home.html", error="Room does not exist.", name=name)

        # Store user info in session
        session["room"] = room
        session["name"] = name

        return redirect(url_for("room"))

    return render_template("home.html")


@app.route("/room")
def room():
    """Chat room view."""
    room = session.get("room")
    name = session.get("name")

    # Prevent direct access without session data
    if not room or not name or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])


@socketio.on("message")
def handle_message(data):
    """Handle sending and storing chat messages."""
    room = session.get("room")
    name = session.get("name")

    if room not in rooms or not name:
        return

    content = {"name": name, "message": data["data"]}
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{name} said: {data['data']}")


@socketio.on("connect")
def handle_connect(auth=None):
    """Handle user connection and joining a room."""
    room = session.get("room")
    name = session.get("name")

    if not room or not name or room not in rooms:
        return

    join_room(room)
    send({"name": name, "message": "has entered the room."}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")


@socketio.on("disconnect")
def handle_disconnect():
    """Handle user disconnection and cleanup."""
    room = session.get("room")
    name = session.get("name")

    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({"name": name, "message": "has left the room."}, to=room)
    print(f"{name} left room {room}")


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
