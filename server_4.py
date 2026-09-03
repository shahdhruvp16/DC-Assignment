"""
Server 4: Delivery Partner
Distributed Food Delivery System
Port: 8003
"""
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer
import time
from datetime import datetime
from socketserver import ThreadingMixIn

print("\n" + "="*50)
print("   DELIVERY PARTNER (Server 4)")
print("="*50 + "\n")

class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass

# Create Server
server = ThreadedXMLRPCServer(("localhost", 8003))
print("✓ Server 4 running on port 8003...\n")

# ============================================================
# CHANDY-LAMPORT GLOBAL SNAPSHOT
# ============================================================

snapshot_sessions = {}
snapshot_counter = 0

PROCESS_ID = "P3"

INCOMING_CHANNELS = {
    "Server-2": "P1",
    "Server-3": "P2"
}

OUTGOING_CHANNELS = {
    "Server-1": "P0"
}

# ============================================================
# CHANDY-LAMPORT SNAPSHOT FUNCTIONS
# ============================================================

def record_snapshot_state(snapshot_id):
    """
    Record the local state of this process.
    """

    if snapshot_id in snapshot_sessions:
        return snapshot_sessions[snapshot_id]

    # Take a copy of the current process state
    local_state_snapshot = {
        "process_id": PROCESS_ID,
        "server": "Server-4",
        "vector_clock": vc.get(),
        "state": local_state.copy(),
        "event_count": len(event_log),
        "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3]
    }

    # Create channel recording state
    channels = {}

    for channel in INCOMING_CHANNELS:
        channels[channel] = {
            "recording": True,
            "messages": []
        }

    snapshot_sessions[snapshot_id] = {
        "snapshot_id": snapshot_id,
        "recorded": True,
        "local_state": local_state_snapshot,
        "channels": channels,
        "completed": False
    }

    print(
        f"[SNAPSHOT] {PROCESS_ID} recorded local state "
        f"for Snapshot #{snapshot_id}"
    )

    return snapshot_sessions[snapshot_id]

# =====================================================
# VECTOR CLOCK
# =====================================================

class VectorClock:
    """Logical clock for distributed system"""
    def __init__(self, process_id, num_processes=4):
        self.process_id = process_id
        self.clock = [0] * num_processes
    
    def increment(self):
        """Increment on internal or send event"""
        self.clock[self.process_id] += 1
        return self.clock.copy()
    
    def update(self, received_clock):
        """Update on receive event"""
        self.clock[self.process_id] += 1
        for i in range(len(self.clock)):
            self.clock[i] = max(self.clock[i], received_clock[i])
        return self.clock.copy()
    
    def get(self):
        return self.clock.copy()


# =====================================================
# STATE & LOGGING
# =====================================================

# Process ID: 3 (Delivery Partner)
vc = VectorClock(3, 4)

# Statistics
request_count = 0
delivery_count = 0
location_updates = 0
event_log = []

# Local State
local_state = {
    "role": "Delivery Partner",
    "current_location": "DEPOT",
    "deliveries_completed": 0,
    "status": "ACTIVE",
    "vehicle_status": "IDLE",
    "last_action": "initialized"
}

# Active deliveries
active_deliveries = {}

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def log_event(event_type, description, already_updated=False):
    """Log event with vector clock"""
    global event_log, request_count

    # INTERNAL and SEND events increment the local clock.
    # RECEIVE events increment the clock unless it has already
    # been updated using the sender's vector clock.
    if not already_updated:
        if event_type in ("INTERNAL", "SEND", "RECEIVE"):
            current_vc = vc.increment()
        else:
            current_vc = vc.get()
    else:
        current_vc = vc.get()

    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    event = {
        "timestamp": timestamp,
        "process": "P3-Server4",
        "event_type": event_type,
        "vector_clock": current_vc,
        "description": description
    }

    event_log.append(event)

    print(
        f"[{timestamp}] P3 [{event_type}] "
        f"VC{current_vc} - {description}"
    )

    request_count += 1

    return current_vc

# =====================================================
# XML-RPC FUNCTIONS
# =====================================================

def health():
    """Health check"""
    log_event("INTERNAL", "Health check performed")
    return "Server 4 (Delivery Partner) is Healthy ✓"

def accept_delivery(order_id, restaurant, customer_address,
                    from_server, sender_vc=None):

    global delivery_count

    # Chandy-Lamport channel recording
    record_channel_message(
        from_server,
        f"Delivery assignment #{order_id} received"
    )

    if sender_vc is not None:
        vc.update(sender_vc)
    else:
        vc.increment()

    receive_vc = log_event(
        "RECEIVE",
        f"Delivery assignment #{order_id} from {from_server}: "
        f"{restaurant} -> {customer_address}",
        already_updated=True
    )

    delivery_count += 1
    local_state["vehicle_status"] = "EN_ROUTE"

    # Store active delivery
    active_deliveries[str(order_id)] = {
        "restaurant": restaurant,
        "destination": customer_address,
        "status": "PICKED_UP"
    }

    return {
        "order_id": order_id,
        "status": "ACCEPTED",
        "vector_clock": receive_vc,
        "message": "Delivery accepted"
    }

def update_location(order_id, location):
    """Update delivery location (internal action)"""
    global location_updates

    log_event("INTERNAL", f"Updating location for delivery #{order_id} to {location}")

    location_updates += 1
    local_state["current_location"] = location
    local_state["last_action"] = f"At {location}"

    order_key = str(order_id)

    if order_key in active_deliveries:
        active_deliveries[order_key]["status"] = "IN_TRANSIT"
        active_deliveries[order_key]["location"] = location

    return {
        "order_id": order_id,
        "location": location,
        "vector_clock": vc.get()
    }

def confirm_delivery(order_id, customer_address):
    """Confirm delivery (internal action)"""
    log_event(
        "INTERNAL",
        f"Confirming delivery #{order_id} at {customer_address}"
    )

    order_key = str(order_id)

    if order_key in active_deliveries:
        active_deliveries[order_key]["status"] = "DELIVERED"

    local_state["deliveries_completed"] += 1
    local_state["vehicle_status"] = "IDLE"
    local_state["current_location"] = "DEPOT"

    # Simulate delivery confirmation time
    time.sleep(0.5)

    return {
        "order_id": order_id,
        "status": "DELIVERED",
        "vector_clock": vc.get()
    }

def send_delivery_update(central_processor, order_id, status, location):
    """Send delivery status directly from Server-4 to Server-1."""

    central_url = "http://localhost:8000/"

    send_vc = log_event(
        "SEND",
        f"Sending delivery update #{order_id} to Server-1: "
        f"{status} at {location}"
    )

    central_client = xmlrpc.client.ServerProxy(
        central_url,
        allow_none=True
    )

    result = central_client.receive_delivery_status(
        order_id,
        status,
        location,
        "Server-4",
        send_vc
    )

    return result

def get_delivery_status():
    """Get all delivery statuses"""
    log_event("INTERNAL", "Delivery status query")
    
    return {
        "active_deliveries": len(active_deliveries),
        "total_completed": local_state["deliveries_completed"],
        "current_location": local_state["current_location"],
        "vehicle_status": local_state["vehicle_status"],
        "vector_clock": vc.get()
    }

def get_state():
    """Get current state"""
    return {
        "process": "P3-Server4",
        "local_state": local_state.copy(),
        "vector_clock": vc.get(),
        "active_deliveries": active_deliveries.copy(),
        "statistics": {
            "total_requests": request_count,
            "deliveries_accepted": delivery_count,
            "location_updates": location_updates,
            "events_logged": len(event_log)
        }
    }

def get_event_log():
    """Get all events"""
    return event_log.copy()

def sync_with_server(server_name, operation, data):
    """Synchronize with other servers"""
    log_event("INTERNAL", f"Syncing with {server_name}: {operation}")
    
    return {
        "status": "SYNCED",
        "vector_clock": vc.get()
    }

def receive_marker(snapshot_id, from_server):
    """
    Receive a Chandy-Lamport marker.

    First marker:
      1. Record local state.
      2. Start recording all incoming channels.
      3. Stop recording the channel on which marker arrived.
      4. Send markers through outgoing channels.

    Later markers:
      Stop recording the corresponding incoming channel.
    """

    print(
        f"[SNAPSHOT] {PROCESS_ID} received MARKER "
        f"for Snapshot #{snapshot_id} from {from_server}"
    )

    first_marker = snapshot_id not in snapshot_sessions

    if first_marker:

        # Record local state first
        record_snapshot_state(snapshot_id)

        # Stop recording the channel from which
        # the first marker arrived.
        if from_server in snapshot_sessions[snapshot_id]["channels"]:
            snapshot_sessions[snapshot_id]["channels"][
                from_server
            ]["recording"] = False

        # Forward marker through outgoing channels
        send_snapshot_markers(snapshot_id)

    else:

        # Subsequent marker closes this incoming channel
        if from_server in snapshot_sessions[snapshot_id]["channels"]:
            snapshot_sessions[snapshot_id]["channels"][
                from_server
            ]["recording"] = False

    check_snapshot_completion(snapshot_id)

    return {
        "snapshot_id": snapshot_id,
        "process": PROCESS_ID,
        "status": "MARKER_RECEIVED"
    }

def record_channel_message(from_server, message_description):
    """
    Record an application message as an in-transit message
    for every active Chandy-Lamport snapshot where the
    incoming channel is still being recorded.
    """

    for snapshot_id, snapshot in snapshot_sessions.items():

        # Ignore snapshots that have not recorded local state
        if not snapshot["recorded"]:
            continue

        # Ignore if this server has no channel from this sender
        if from_server not in snapshot["channels"]:
            continue

        channel = snapshot["channels"][from_server]

        # Record message only while this channel is open
        if channel["recording"]:

            channel["messages"].append({
                "from": from_server,
                "to": PROCESS_ID,
                "description": message_description,
                "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3]
            })

            print(
                f"[SNAPSHOT #{snapshot_id}] "
                f"{PROCESS_ID} recorded in-transit message "
                f"from {from_server}: {message_description}"
            )

def check_snapshot_completion(snapshot_id):

    if snapshot_id not in snapshot_sessions:
        return False

    snapshot = snapshot_sessions[snapshot_id]

    all_channels_closed = all(
        not channel["recording"]
        for channel in snapshot["channels"].values()
    )

    if all_channels_closed:
        snapshot["completed"] = True

        print(
            f"[SNAPSHOT] {PROCESS_ID} completed "
            f"Snapshot #{snapshot_id}"
        )

    return snapshot["completed"]

def get_snapshot(snapshot_id):

    if snapshot_id not in snapshot_sessions:
        return {
            "snapshot_id": snapshot_id,
            "process": PROCESS_ID,
            "recorded": False,
            "message": "Snapshot not found"
        }

    snapshot = snapshot_sessions[snapshot_id]

    return {
        "snapshot_id": snapshot_id,
        "process": PROCESS_ID,
        "recorded": snapshot["recorded"],
        "completed": snapshot["completed"],
        "local_state": snapshot["local_state"],
        "channels": snapshot["channels"]
    }
    
def send_snapshot_markers(snapshot_id):

    central_server = xmlrpc.client.ServerProxy(
        "http://localhost:8000/",
        allow_none=True
    )

    central_server.receive_marker(
        snapshot_id,
        "Server-4"
    )

# =====================================================
# REGISTER FUNCTIONS
# =====================================================

server.register_function(health, "health")
server.register_function(accept_delivery, "accept_delivery")
server.register_function(update_location, "update_location")
server.register_function(confirm_delivery, "confirm_delivery")
server.register_function(send_delivery_update, "send_delivery_update")
server.register_function(get_delivery_status, "get_delivery_status")
server.register_function(get_state, "get_state")
server.register_function(get_event_log, "get_event_log")
server.register_function(sync_with_server, "sync_with_server")
server.register_function(get_snapshot, "get_snapshot")
server.register_function(receive_marker, "receive_marker")

# =====================================================
# RUN SERVER
# =====================================================

print("Registered Functions:")
print("  ✓ health()")
print("  ✓ accept_delivery(order_id, restaurant, customer_address, from_server, sender_vc=None)")
print("  ✓ update_location(order_id, location)")
print("  ✓ confirm_delivery(order_id, customer_address)")
print("  ✓ send_delivery_update(central_processor, order_id, status, location)")
print("  ✓ get_delivery_status()")
print("  ✓ get_state()")
print("  ✓ get_event_log()")
print("  ✓ sync_with_server(server_name, operation, data)")
print("\nWaiting for client requests...\n")

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\n\nServer 4 Shutting Down...")
    print(f"Total Requests Processed: {request_count}")
    print(f"Total Deliveries Completed: {local_state['deliveries_completed']}")
    print(f"Total Events Logged: {len(event_log)}")
    print("="*50)
