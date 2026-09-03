"""
Server 1: Central Order Processor
Distributed Food Delivery System
Port: 8000
"""
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer
import time
import json
from datetime import datetime
from socketserver import ThreadingMixIn

print("\n" + "="*50)
print("   CENTRAL ORDER PROCESSOR (Server 1)")
print("="*50 + "\n")

class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass

# Create Server
server = ThreadedXMLRPCServer(("localhost", 8000))
print("✓ Server 1 running on port 8000...\n")

# ============================================================
# CHANDY-LAMPORT GLOBAL SNAPSHOT
# ============================================================

snapshot_sessions = {}
snapshot_counter = 0

PROCESS_ID = "P0"

INCOMING_CHANNELS = {
    "Server-4": "P3"
}

OUTGOING_CHANNELS = {
    "Server-2": "P1",
    "Server-3": "P2"
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
        "server": "Server-1",
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

# Process ID: 0 (Central Processor)
vc = VectorClock(0, 4)

# Statistics
request_count = 0
order_count = 0
snapshot_count = 0
event_log = []

# Local State
local_state = {
    "role": "Central Order Processor",
    "orders_received": 0,
    "orders_processed": 0,
    "status": "ACTIVE",
    "last_action": "initialized"
}

# Received Messages
received_messages = []

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def log_event(event_type, description, already_updated=False):
    """Log event with vector clock"""
    global event_log, request_count

    # Increment the vector clock for INTERNAL and SEND events.
    # For RECEIVE events, the vector clock may already have been
    # updated with the sender's vector clock.
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
        "process": "P0-Server1",
        "event_type": event_type,
        "vector_clock": current_vc,
        "description": description
    }

    event_log.append(event)

    print(
        f"[{timestamp}] P0 [{event_type}] "
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
    return "Server 1 (Central Processor) is Healthy ✓"

def receive_order(order_id, customer_name, items, from_server, sender_vc=None):
    """Receive order from client/restaurant"""

    global order_count

    # Update vector clock using the sender's vector clock.
    # vc.update() already increments this process's own component.
    if sender_vc is not None:
        vc.update(sender_vc)
    else:
        vc.increment()

    # Log RECEIVE without incrementing the vector clock again.
    receive_vc = log_event(
        "RECEIVE",
        f"Order #{order_id} from {from_server}: "
        f"{customer_name} ordered {items}",
        already_updated=True
    )

    order_count += 1
    local_state["orders_received"] += 1

    # Process order internally.
    process_vc = log_event(
        "INTERNAL",
        f"Processing order #{order_id}"
    )

    local_state["orders_processed"] += 1

    # Send confirmation.
    send_vc = log_event(
        "SEND",
        f"Sending order confirmation for #{order_id}"
    )

    result = {
        "order_id": order_id,
        "status": "RECEIVED",
        "vector_clock": send_vc,
        "message": "Order received and processed"
    }

    return result
    
def send_order_to_restaurant(
    restaurant_server,
    order_id,
    customer_name,
    items
):
    """Send an order directly from Server-1 to Restaurant Server."""

    restaurant_urls = {
        "Server-2": "http://localhost:8001/",
        "Server-3": "http://localhost:8002/"
    }

    if restaurant_server not in restaurant_urls:
        raise ValueError(f"Invalid restaurant server: {restaurant_server}")

    # IMPORTANT:
    # Increment/log SEND BEFORE making the RPC call.
    send_vc = log_event(
        "SEND",
        f"Sending order #{order_id} to {restaurant_server}"
    )

    restaurant_client = xmlrpc.client.ServerProxy(
        restaurant_urls[restaurant_server],
        allow_none=True
    )

    result = restaurant_client.receive_order(
        order_id,
        customer_name,
        items,
        "Server-1",
        send_vc
    )

    return result

def receive_delivery_status(
    order_id, status, location, from_server, sender_vc=None
):

    # Chandy-Lamport channel recording
    record_channel_message(
        from_server,
        f"Delivery update #{order_id}: {status}"
    )

    if sender_vc is not None:
        vc.update(sender_vc)
    else:
        vc.increment()

    receive_vc = log_event(
        "RECEIVE",
        f"Delivery update for order #{order_id} from "
        f"{from_server}: {status} at {location}",
        already_updated=True
    )

    return {
        "order_id": order_id,
        "status": status,
        "location": location,
        "vector_clock": receive_vc,
        "message": "Delivery status received by Server-1"
    }

def initiate_snapshot():

    global snapshot_counter

    snapshot_counter += 1
    snapshot_id = snapshot_counter

    print("\n" + "=" * 70)
    print(f"CHANDY-LAMPORT SNAPSHOT #{snapshot_id}")
    print("=" * 70)

    # P0 records its own local state first
    record_snapshot_state(snapshot_id)

    # P0 sends marker messages
    send_snapshot_markers(snapshot_id)

    return {
        "snapshot_id": snapshot_id,
        "initiator": PROCESS_ID,
        "status": "SNAPSHOT_INITIATED"
    }

def get_state():
    """Get current state"""
    return {
        "process": "P0-Server1",
        "local_state": local_state.copy(),
        "vector_clock": vc.get(),
        "statistics": {
            "total_requests": request_count,
            "orders_processed": order_count,
            "snapshots_initiated": snapshot_count,
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

    # Marker P0 -> P1
    restaurant1 = xmlrpc.client.ServerProxy(
        "http://localhost:8001/",
        allow_none=True
    )

    restaurant1.receive_marker(
        snapshot_id,
        "Server-1"
    )

    # Marker P0 -> P2
    restaurant2 = xmlrpc.client.ServerProxy(
        "http://localhost:8002/",
        allow_none=True
    )

    restaurant2.receive_marker(
        snapshot_id,
        "Server-1"
    )

# =====================================================
# REGISTER FUNCTIONS
# =====================================================

server.register_function(health, "health")
server.register_function(receive_order, "receive_order")
server.register_function(send_order_to_restaurant, "send_order_to_restaurant")
server.register_function(receive_delivery_status, "receive_delivery_status")
server.register_function(initiate_snapshot, "initiate_snapshot")
server.register_function(get_state, "get_state")
server.register_function(get_event_log, "get_event_log")
server.register_function(sync_with_server, "sync_with_server")
server.register_function(get_snapshot, "get_snapshot")
server.register_function(receive_marker, "receive_marker")
server.register_function(initiate_snapshot, "initiate_snapshot")

# =====================================================
# RUN SERVER
# =====================================================

print("Registered Functions:")
print("  ✓ health()")
print("  ✓ receive_order(order_id, customer_name, items, from_server)")
print("  ✓ send_order_to_restaurant(restaurant_server, order_id, items)")
print("  ✓ receive_delivery_status(delivery_partner, order_id, status, location)")
print("  ✓ initiate_snapshot()")
print("  ✓ get_state()")
print("  ✓ get_event_log()")
print("  ✓ sync_with_server(server_name, operation, data)")
print("\nWaiting for client requests...\n")

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\n\nServer 1 Shutting Down...")
    print(f"Total Requests Processed: {request_count}")
    print(f"Total Orders Processed: {order_count}")
    print(f"Total Events Logged: {len(event_log)}")
    print("="*50)
