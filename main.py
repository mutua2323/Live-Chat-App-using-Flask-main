from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, SocketIO, send
import random
from string import ascii_uppercase

#Initialising the flask application
app = Flask(__name__)

#Confirguring the flask app
app.config["SECRET_KEY"] = "qwertymnbvcxz"

#Connecting/Integerating socketio
#We will create a socket and pass it to our application
#thus, socketio = SocketIO(application_name)
socketio = SocketIO(app)

rooms = {}  
#The dictionary which will store the information of the different rooms we have
# like the code associated with the room and the messages present in the room

def generate_unique_code(length):
    while True: #If room already exists, we don't need to generate any code
        code = ""
        for _ in range(length): #Here, _ is an anonymous variable, because we dont care the count of this iterable
            code += random.choice(ascii_uppercase)

        if code not in rooms:   #This checks if the code exists in the dictionary "rooms"
            break
        
    return code

#Creating route for homepage
#Syntax: @application_name.rote(route_name, methods_that_can_be_sent_to_this_route)
# GET is a default methods that retrieves whatever the function home returns
# POST allows us to enter/post data to the route
@app.route("/", methods=["POST", "GET"])
def home():
    session.clear() #When redirected to the home page, the session gets cleared
    if request.method=="POST":      #grabs the form data
        name = request.form.get("name")
        code = request.form.get("code")
        create = request.form.get("create", False)
        join = request.form.get("join", False)

        if not name:
            return render_template("home.html", error="Please eneter a name.", code=code, name=name)
        # Whenever we send a post request to the template (basically refresh the page),
        # We need to pass the name and code back to the template 
        # because when we refresh a page, the page gets rid of whatever we type.
                
        if join != False and not code:
            return render_template("home.html", error="Please eneter a room code.")
        
        room = code
        if create != False:         #Creating a new room
            room = generate_unique_code(4)
            rooms[room] = {"members" : 0, "messages": []}
            #by default, there are 0 members and the messages are stored in the form of lists
        elif code not in rooms:     #If they are joining a room and the code entered does not exist
            return render_template("home.html", error="Room does not exist.")
    
        session["room"] = room  # Stores information of the room
        session["name"] = name
        # Session is a semi-permanent/temporary way to store the information of the user.
        # We store data in sessions

        # Redirecting the person to a new page, which is the chat page that they are joining
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room")
    # To avoid the user to directly enter the room, we add a guard condition/clause
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    
    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):  # To transmit the data from the server to all the other members in the room
    room = session.get("room")  # To check which room
    if room not in rooms:
        return 
    
    # The message along with the name of the user is stored in the form of a dictionary
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }

    send(content, to=room)
    rooms[room]["messages"].append(content) # Adds the content to the main dict. so that it is stored, acts like history
    print(f"{session.get('name')} said: {data['data']}")        # The debug statement gets printed in the server logs/terminal

@socketio.on("connect")
def connect(auth):      # The parameter is passed, but not used anywhere
    # getting the room and the name of the user.
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return 
    # This makes sure that someone is not trying to connect to our socket before going through the home page
    # Unless the user has a room, there will be no messages or names sent
    if room not in rooms:   # If room is not valid/existent
        leave_room(room)
        return
    
    join_room(room)     # Puts the user in the socket room
    # Emit/send a message (a JSON message here) to all the people present in the room
    send({"name": name, "message": "has entered the room."}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}") # debug statement that appears in the terminal

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
            # If everyone left the room, there is no need to store any information, 
            # so we can delete the information of that particular room.

    send({"name": name, "message": "has left the room."}, to=room)
    print(f"{name} left room {room}")   # debug statement that appears in the terminal

# Running the application
if __name__ == "__main__":
    socketio.run(app, debug=True)
