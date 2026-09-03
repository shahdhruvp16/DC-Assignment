"""
Server 2: Restaurant 1
Distributed Food Delivery System
Port: 8001
"""
from asyncio import Server
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer
import time
import json
from datetime import datetime
from socketserver import ThreadingMixIn

print("\n" + "="*50)
print("     RESTAURANT 1 (Server 2)")
print("="*50 + "\n")

class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass

# Create Server
server = ThreadedXMLRPCServer(("localhost", 8001))
print("✓ Server 2 running on port 8001...\n")

# ============================================================
# CHANDY-LAMPORT GLOBAL SNAPSHOT
# ============================================================

snapshot_sessions = {}
snapshot_counter = 0

PROCESS_ID = "P1"

INCOMING_CHANNELS = {
    "Server-1": "P0"
}

OUTGOING_CHANNELS = {
    "Server-4": "P3"
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
        "server": "Server-2",
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

# Process ID: 1 (Restaurant 1)
vc = VectorClock(1, 4)

# Statistics
request_count = 0
order_count = 0
preparation_count = 0
event_log = []

# Local State
local_state = {
    "role": "Restaurant 1",
    "orders_received": 0,
    "orders_prepared": 0,
    "status": "ACTIVE",
    "kitchen_status": "IDLE",
    "last_action": "initialized"
}

# In-progress orders
orders_in_progress = {}

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def log_event(event_type, description, already_updated=False):
    """Log event with vector clock"""
    global event_log, request_count

    # INTERNAL and SEND events increment the local clock.
    # RECEIVE events increment the clock unless it was already
    # updated using the sender's vector clock.
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
        "process": "P1-Server2",
        "event_type": event_type,
        "vector_clock": current_vc,
        "description": description
    }

    event_log.append(event)

    print(
        f"[{timestamp}] P1 [{event_type}] "
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
    return "Server 2 (Restaurant 1) is Healthy ✓"

def receive_order(order_id, customer_name, items, from_server, sender_vc=None):

    global order_count

    # Chandy-Lamport:
    # Check whether this message is in transit for any active snapshot.
    record_channel_message(
        from_server,
        f"Order #{order_id} received"
    )

    if sender_vc is not None:
        vc.update(sender_vc)
    else:
        vc.increment()

    receive_vc = log_event(
        "RECEIVE",
        f"Order #{order_id} from {from_server}: {customer_name} ordered {items}",
        already_updated=True
    )

    order_count += 1
    local_state["orders_received"] += 1
    local_state["kitchen_status"] = "COOKING"

    orders_in_progress[str(order_id)] = {
        "customer": customer_name,
        "items": items,
        "status": "PREPARING"
    }

    return {
        "order_id": order_id,
        "status": "RECEIVED",
        "vector_clock": receive_vc,
        "message": "Order received at Restaurant 1"
    }

def prepare_order(order_id):
    """Prepare the order (internal action)"""
    global preparation_count
    
    log_event(
    "INTERNAL",
    f"Preparing order #{order_id} in kitchen"
    )
    
    if str(order_id) in orders_in_progress:
        orders_in_progress[str(order_id)]["status"] = "PREPARED"
    
    preparation_count += 1
    local_state["orders_prepared"] += 1
    local_state["last_action"] = f"Prepared order #{order_id}"
    
    # Simulate cooking time
    time.sleep(1)
    
    return {
        "order_id": order_id,
        "status": "READY",
        "vector_clock": vc.get()
    }

def send_delivery_update(delivery_partner, order_id):
    """Send prepared order directly from Restaurant 1 to Server-4."""

    delivery_url = "http://localhost:8003/"

    send_vc = log_event(
        "SEND",
        f"Sending order #{order_id} to Server-4 for delivery"
    )

    delivery_client = xmlrpc.client.ServerProxy(
        delivery_url,
        allow_none=True
    )

    result = delivery_client.accept_delivery(
        order_id,
        "Restaurant 1",
        f"Address-{orders_in_progress[str(order_id)]['customer']}",
        "Server-2",
        send_vc
    )

    return result

def receive_delivery_confirmation(
    order_id,
    status,
    location,
    sender_vc=None
):
    """Receive delivery confirmation"""

    # Update vector clock from sender.
    if sender_vc is not None:
        vc.update(sender_vc)
    else:
        vc.increment()

    # Log RECEIVE without incrementing again.
    receive_vc = log_event(
        "RECEIVE",
        f"Delivery confirmation for order #{order_id}: "
        f"{status} at {location}",
        already_updated=True
    )

    if str(order_id) in orders_in_progress:
        orders_in_progress[str(order_id)]["status"] = "DELIVERED"

    return {
        "acknowledged": True,
        "vector_clock": receive_vc
    }

def get_kitchen_status():
    """Get kitchen status"""
    log_event("INTERNAL", "Kitchen status query")
    
    return {
        "kitchen_status": local_state["kitchen_status"],
        "orders_in_progress": len(orders_in_progress),
        "vector_clock": vc.get()
    }

def get_state():
    """Get current state"""
    return {
        "process": "P1-Server2",
        "local_state": local_state.copy(),
        "vector_clock": vc.get(),
        "orders_in_progress": orders_in_progress.copy(),
        "statistics": {
            "total_requests": request_count,
            "orders_received": order_count,
            "orders_prepared": preparation_count,
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

    delivery_server = xmlrpc.client.ServerProxy(
        "http://localhost:8003/",
        allow_none=True
    )

    delivery_server.receive_marker(
        snapshot_id,
        "Server-2"
    )

# =====================================================
# REGISTER FUNCTIONS
# =====================================================

server.register_function(health, "health")
server.register_function(receive_order, "receive_order")
server.register_function(prepare_order, "prepare_order")
server.register_function(send_delivery_update, "send_delivery_update")
server.register_function(receive_delivery_confirmation, "receive_delivery_confirmation")
server.register_function(get_kitchen_status, "get_kitchen_status")
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
print("  ✓ receive_order(order_id, customer_name, items, from_server, sender_vc=None)")
print("  ✓ prepare_order(order_id)")
print("  ✓ send_delivery_update(delivery_partner, order_id)")
print("  ✓ receive_delivery_confirmation(order_id, status, location, sender_vc=None)")
print("  ✓ get_kitchen_status()")
print("  ✓ get_state()")
print("  ✓ get_event_log()")
print("  ✓ sync_with_server(server_name, operation, data)")
print("\nWaiting for client requests...\n")

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\n\nServer 2 Shutting Down...")
    print(f"Total Requests Processed: {request_count}")
    print(f"Total Orders Prepared: {preparation_count}")
    print(f"Total Events Logged: {len(event_log)}")
    print("="*50)
