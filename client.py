import xmlrpc.client
import random
import time

# =====================================================
# SERVER CONFIGURATION
# =====================================================

servers = {
    "Server-1": {
        "url": "http://localhost:8000/",
        "name": "Central Order Processor",
        "port": 8000
    },
    "Server-2": {
        "url": "http://localhost:8001/",
        "name": "Restaurant 1",
        "port": 8001
    },
    "Server-3": {
        "url": "http://localhost:8002/",
        "name": "Restaurant 2",
        "port": 8002
    },
    "Server-4": {
        "url": "http://localhost:8003/",
        "name": "Delivery Partner",
        "port": 8003
    }
}

# This dashboard measures FOOD-ORDER ASSIGNMENTS, not arbitrary RPC/event counts.
restaurant_load = {
    "Server-2": 0,
    "Server-3": 0
}

active_servers = []
all_events = []


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def check_server_health():
    """Check health of all servers."""
    global active_servers

    print("\n" + "-" * 70)
    print("CHECKING SERVER HEALTH")
    print("-" * 70)

    active_servers = []

    for server_name, server_info in servers.items():
        try:
            client = xmlrpc.client.ServerProxy(server_info["url"], allow_none=True)
            status = client.health()
            print(
                f"✓ {server_name:12} ({server_info['name']:25}): {status}"
            )
            active_servers.append(server_name)
        except Exception as e:
            print(
                f"✗ {server_name:12} ({server_info['name']:25}): "
                f"DOWN - {str(e)[:50]}"
            )

    print(f"\nActive servers: {len(active_servers)}/{len(servers)}")
    return len(active_servers) == len(servers)


def collect_all_events():
    """Collect events from all currently active servers."""
    global all_events

    print("\n" + "-" * 70)
    print("COLLECTING EVENTS FROM ALL SERVERS")
    print("-" * 70)

    all_events = []
    failed_servers = []

    for server_name in active_servers:
        try:
            client = xmlrpc.client.ServerProxy(
                servers[server_name]["url"], allow_none=True
            )
            events = client.get_event_log()

            if not isinstance(events, list):
                raise ValueError("get_event_log() did not return a list")

            print(f"✓ {server_name}: Collected {len(events)} events")
            all_events.extend(events)

        except Exception as e:
            failed_servers.append(server_name)
            print(
                f"✗ {server_name}: Error collecting events - "
                f"{str(e)[:50]}"
            )

    print(f"\nTotal Events Collected: {len(all_events)}")

    if failed_servers:
        print(f"⚠ Failed servers: {', '.join(failed_servers)}")
        return False

    return True


def display_event_log():
    """Display formatted event log."""
    print("\n" + "=" * 70)
    print("DISTRIBUTED SYSTEM EVENT LOG")
    print("=" * 70 + "\n")

    if not all_events:
        print("No events to display.")
        return

    sorted_events = sorted(
        all_events,
        key=lambda e: e.get("timestamp", "")
    )

    for i, event in enumerate(sorted_events, 1):
        print(
            f"{i:3d}. [{event.get('timestamp', 'N/A')}] "
            f"{event.get('process', 'N/A'):12} "
            f"[{event.get('event_type', 'N/A'):8}] "
            f"VC{event.get('vector_clock', 'N/A')} - "
            f"{event.get('description', 'N/A')}"
        )

    print("\n" + "=" * 70)


# =====================================================
# VECTOR CLOCK ANALYSIS
# =====================================================

def vector_clock_happens_before(vc1, vc2):
    """
    Return True if vc1 happens-before vc2.

    vc1 < vc2 means:
      - every component of vc1 <= vc2
      - at least one component is strictly smaller
    """
    if not isinstance(vc1, (list, tuple)):
        return False
    if not isinstance(vc2, (list, tuple)):
        return False
    if len(vc1) != len(vc2):
        return False

    less_or_equal = all(a <= b for a, b in zip(vc1, vc2))
    strictly_less = any(a < b for a, b in zip(vc1, vc2))

    return less_or_equal and strictly_less


def vector_clocks_concurrent(vc1, vc2):
    """Return True only when neither vector clock happens-before the other."""
    if not isinstance(vc1, (list, tuple)):
        return False
    if not isinstance(vc2, (list, tuple)):
        return False
    if len(vc1) != len(vc2):
        return False

    return (
        not vector_clock_happens_before(vc1, vc2)
        and not vector_clock_happens_before(vc2, vc1)
        and list(vc1) != list(vc2)
    )


def vector_clock_configuration_warning():
    """
    Detect the current project's likely independent-clock configuration.

    If each process has only its own component increasing in all events, the
    clocks are not carrying message causality between processes.
    """
    if not all_events:
        return None

    process_clocks = {}

    for event in all_events:
        process = event.get("process")
        vc = event.get("vector_clock")

        if process is None or not isinstance(vc, list) or len(vc) != 4:
            continue

        process_clocks.setdefault(process, []).append(vc)

    independent = True

    for process, clocks in process_clocks.items():
        if not clocks:
            continue

        # Determine which component this process appears to own.
        latest = clocks[-1]
        non_zero = [i for i, value in enumerate(latest) if value > 0]

        if len(non_zero) != 1:
            independent = False
            break

    if independent and len(process_clocks) > 1:
        return (
            "WARNING: Current server vector clocks appear independent. "
            "The RPC messages are not exchanging sender vector clocks, so "
            "cross-process causality is not represented correctly."
        )

    return None


def analyze_concurrent_events():
    """Analyze concurrent events using vector clocks."""
    print("\n" + "-" * 70)
    print("CONCURRENT EVENT ANALYSIS")
    print("-" * 70)

    if not all_events:
        print("No events available. Collect events first.")
        return

    warning = vector_clock_configuration_warning()
    if warning:
        print(f"\n⚠ {warning}")
        print(
            "The count below is therefore NOT a reliable distributed "
            "concurrency result until the server vector clocks are fixed."
        )

    concurrent_pairs = []

    for i in range(len(all_events)):
        for j in range(i + 1, len(all_events)):
            event1 = all_events[i]
            event2 = all_events[j]

            if event1.get("process") == event2.get("process"):
                continue

            vc1 = event1.get("vector_clock")
            vc2 = event2.get("vector_clock")

            if vector_clocks_concurrent(vc1, vc2):
                concurrent_pairs.append((event1, event2))

    print(f"\nConcurrent Events Found: {len(concurrent_pairs)}\n")

    for i, (e1, e2) in enumerate(concurrent_pairs[:10], 1):
        print(
            f"{i}. {e1.get('process')} VC{e1.get('vector_clock')} "
            f"|| {e2.get('process')} VC{e2.get('vector_clock')}"
        )

    if len(concurrent_pairs) > 10:
        print(
            f"... and {len(concurrent_pairs) - 10} more concurrent pairs"
        )


# =====================================================
# SNAPSHOT
# =====================================================

def initiate_snapshot():
    """
    Initiate and verify a formal Chandy-Lamport global snapshot.

    The snapshot contains:
      1. Local state of every process
      2. Vector clock of every process
      3. State of every incoming communication channel
      4. In-transit messages recorded on open channels
      5. Completion status of every process
    """

    print("\n" + "=" * 70)
    print("INITIATING CHANDY-LAMPORT GLOBAL SNAPSHOT")
    print("=" * 70)

    expected_servers = list(servers.keys())
    snapshot_states = {}

    # =========================================================
    # 1. INITIATE SNAPSHOT FROM SERVER-1 / P0
    # =========================================================

    try:
        central_client = xmlrpc.client.ServerProxy(
            servers["Server-1"]["url"],
            allow_none=True
        )

        snapshot = central_client.initiate_snapshot()

        snapshot_id = snapshot["snapshot_id"]

        print(f"\n✓ Snapshot initiated by {snapshot['initiator']}")
        print(f"  Snapshot ID : {snapshot_id}")
        print(f"  Status      : {snapshot['status']}")

    except Exception as e:
        print(f"✗ Could not initiate snapshot: {e}")
        return False

    # =========================================================
    # 2. WAIT FOR MARKER PROPAGATION
    # =========================================================

    print("\n" + "-" * 70)
    print("WAITING FOR MARKER PROPAGATION")
    print("-" * 70)

    # Marker propagation is normally synchronous because the
    # XML-RPC marker calls wait for the next server to respond.
    # A short delay gives all servers time to finish recording.
    time.sleep(0.5)

    # =========================================================
    # 3. COLLECT ACTUAL CHANDY-LAMPORT SNAPSHOT
    # =========================================================

    print("\n" + "-" * 70)
    print("COLLECTING CHANDY-LAMPORT SNAPSHOT FROM ALL SERVERS")
    print("-" * 70)

    for server_name in expected_servers:

        try:
            client = xmlrpc.client.ServerProxy(
                servers[server_name]["url"],
                allow_none=True
            )

            snapshot_state = client.get_snapshot(snapshot_id)

            if not isinstance(snapshot_state, dict):
                raise ValueError(
                    "get_snapshot() did not return a dictionary"
                )

            if not snapshot_state.get("recorded", False):
                raise ValueError(
                    "Process did not record local state"
                )

            snapshot_states[server_name] = snapshot_state

            print(f"\n✓ {server_name}")
            print(
                f"  Process      : "
                f"{snapshot_state.get('process')}"
            )
            print(
                f"  Recorded     : "
                f"{snapshot_state.get('recorded')}"
            )
            print(
                f"  Completed    : "
                f"{snapshot_state.get('completed')}"
            )

            local_state = snapshot_state.get(
                "local_state",
                {}
            )

            print(
                f"  Vector Clock : "
                f"{local_state.get('vector_clock')}"
            )

            print(
                f"  Local State  : "
                f"{local_state.get('state')}"
            )

            channels = snapshot_state.get(
                "channels",
                {}
            )

            if channels:
                print("  Incoming Channels:")

                for channel_name, channel_data in channels.items():

                    print(
                        f"    {channel_name}: "
                        f"recording="
                        f"{channel_data.get('recording')}, "
                        f"messages="
                        f"{len(channel_data.get('messages', []))}"
                    )

                    messages = channel_data.get(
                        "messages",
                        []
                    )

                    for message in messages:
                        print(
                            f"      → {message.get('description')} "
                            f"[{message.get('timestamp')}]"
                        )

            else:
                print("  Incoming Channels: None")

        except Exception as e:

            print(
                f"\n✗ {server_name}: "
                f"Error - {str(e)[:100]}"
            )

    # =========================================================
    # 4. VERIFY ALL PROCESSES WERE CAPTURED
    # =========================================================

    print("\n" + "-" * 70)
    print("CHANDY-LAMPORT SNAPSHOT CONSISTENCY VERIFICATION")
    print("-" * 70)

    captured = set(snapshot_states.keys())
    missing_servers = set(expected_servers) - captured

    if missing_servers:

        print("✗ SNAPSHOT FAILED")

        print(
            "  Missing processes: "
            + ", ".join(sorted(missing_servers))
        )

        print(
            "  A global snapshot requires every process."
        )

        return False

    # =========================================================
    # 5. VERIFY LOCAL STATES
    # =========================================================

    all_recorded = all(
        state.get("recorded", False)
        for state in snapshot_states.values()
    )

    if not all_recorded:

        print(
            "✗ SNAPSHOT FAILED: "
            "One or more processes did not record local state."
        )

        return False

    print("✓ All 4 processes recorded local state")

    # =========================================================
    # 6. VERIFY VECTOR CLOCKS
    # =========================================================

    valid_vcs = True

    for server_name, state in snapshot_states.items():

        local_state = state.get("local_state", {})
        vector_clock = local_state.get("vector_clock")

        if not (
            isinstance(vector_clock, list)
            and len(vector_clock) == 4
            and all(isinstance(x, int) for x in vector_clock)
        ):
            print(
                f"✗ Invalid vector clock in {server_name}: "
                f"{vector_clock}"
            )
            valid_vcs = False

    if not valid_vcs:

        print("✗ SNAPSHOT FAILED: Invalid vector-clock data.")

        return False

    print("✓ All vector clocks are valid")

    # =========================================================
    # 7. VERIFY CHANNEL STRUCTURE
    # =========================================================

    expected_channels = {
        "Server-1": ["Server-4"],
        "Server-2": ["Server-1"],
        "Server-3": ["Server-1"],
        "Server-4": ["Server-2", "Server-3"]
    }

    channels_valid = True

    print("\nIncoming channel verification:")

    for server_name, required_channels in expected_channels.items():

        actual_channels = set(
            snapshot_states[server_name].get(
                "channels",
                {}
            ).keys()
        )

        required_channels_set = set(required_channels)

        if actual_channels != required_channels_set:

            print(
                f"✗ {server_name}: Invalid channel structure"
            )

            print(
                f"  Expected: {sorted(required_channels_set)}"
            )

            print(
                f"  Actual  : {sorted(actual_channels)}"
            )

            channels_valid = False

        else:

            print(
                f"✓ {server_name}: "
                f"{', '.join(required_channels)}"
            )

    if not channels_valid:

        print(
            "\n✗ SNAPSHOT FAILED: "
            "Channel structure is incorrect."
        )

        return False

    print("✓ All communication channels are correctly represented")

    # =========================================================
    # 8. VERIFY ALL CHANNELS CLOSED
    # =========================================================

    all_channels_closed = True

    print("\nChannel recording status:")

    for server_name, state in snapshot_states.items():

        channels = state.get("channels", {})

        for channel_name, channel_data in channels.items():

            recording = channel_data.get(
                "recording",
                True
            )

            message_count = len(
                channel_data.get(
                    "messages",
                    []
                )
            )

            if recording:

                print(
                    f"✗ {server_name} <- {channel_name}: "
                    f"STILL RECORDING"
                )

                all_channels_closed = False

            else:

                print(
                    f"✓ {channel_name} -> {server_name}: "
                    f"CLOSED, "
                    f"{message_count} in-transit message(s)"
                )

    if not all_channels_closed:

        print(
            "\n✗ SNAPSHOT FAILED: "
            "One or more channels are still open."
        )

        return False

    print("✓ All incoming channels are closed")

    # =========================================================
    # 9. VERIFY PROCESS COMPLETION
    # =========================================================

    all_completed = all(
        state.get("completed", False)
        for state in snapshot_states.values()
    )

    if not all_completed:

        print(
            "✗ SNAPSHOT FAILED: "
            "Not all processes completed the snapshot."
        )

        for server_name, state in snapshot_states.items():

            print(
                f"  {server_name}: "
                f"completed={state.get('completed')}"
            )

        return False

    print("✓ All 4 processes completed the snapshot")

    # =========================================================
    # 10. DISPLAY GLOBAL CHANNEL STATE
    # =========================================================

    print("\n" + "-" * 70)
    print("GLOBAL CHANNEL STATE")
    print("-" * 70)

    total_in_transit = 0

    for server_name, state in snapshot_states.items():

        channels = state.get("channels", {})

        for channel_name, channel_data in channels.items():

            messages = channel_data.get(
                "messages",
                []
            )

            total_in_transit += len(messages)

            print(
                f"\nChannel: {channel_name} -> {server_name}"
            )

            if not messages:

                print("  In-transit messages: 0")

            else:

                print(
                    f"  In-transit messages: "
                    f"{len(messages)}"
                )

                for message in messages:

                    print(
                        f"    • {message.get('description')} "
                        f"at {message.get('timestamp')}"
                    )

    print(
        f"\nTotal in-transit messages captured: "
        f"{total_in_transit}"
    )

    # =========================================================
    # 11. FINAL RESULT
    # =========================================================

    print("\n" + "=" * 70)
    print("CHANDY-LAMPORT SNAPSHOT RESULT")
    print("=" * 70)

    print(f"✓ Snapshot ID: {snapshot_id}")
    print("✓ All 4 processes recorded local state")
    print("✓ All vector clocks recorded")
    print("✓ All incoming channels recorded")
    print("✓ All channel markers received")
    print("✓ All channels closed")
    print("✓ In-transit messages checked")
    print("✓ All processes completed the snapshot")

    print(
        "\n✓✓✓ CHANDY-LAMPORT GLOBAL SNAPSHOT "
        "IS COMPLETE ✓✓✓"
    )

    print("=" * 70)

    return True


# =====================================================
# WORKFLOW + LOAD BALANCING
# =====================================================

def choose_restaurant():
    """
    Simple least-loaded restaurant selection.

    Tie-breaking is random so equal loads do not always choose Server-2.
    """
    candidates = [
        server
        for server in ("Server-2", "Server-3")
        if server in active_servers
    ]

    if not candidates:
        raise RuntimeError("No restaurant server is active.")

    minimum = min(restaurant_load[s] for s in candidates)
    least_loaded = [s for s in candidates if restaurant_load[s] == minimum]

    return random.choice(least_loaded)


def simulate_food_delivery_workflow():
    """Simulate a complete food delivery workflow using server-to-server RPC."""

    print("\n" + "=" * 70)
    print("SIMULATING FOOD DELIVERY WORKFLOW")
    print("=" * 70)

    if not check_server_health():
        print("\n✗ All four servers must be active for the demo.")
        return False

    orders = [
        {
            "order_id": 101,
            "customer": "Alice",
            "items": "Pizza + Coke"
        },
        {
            "order_id": 102,
            "customer": "Bob",
            "items": "Burger + Fries"
        },
        {
            "order_id": 103,
            "customer": "Charlie",
            "items": "Pasta + Wine"
        }
    ]

    successful_orders = 0

    for order in orders:

        order_id = order["order_id"]
        customer = order["customer"]
        items = order["items"]

        restaurant_name = None

        print(
            f"\n--- Processing Order #{order_id} "
            f"({customer}) ---"
        )

        try:

            # =================================================
            # 1. CLIENT → SERVER-1
            # =================================================

            central_client = xmlrpc.client.ServerProxy(
                servers["Server-1"]["url"],
                allow_none=True
            )

            central_state = central_client.get_state()
            central_vc = central_state.get(
                "vector_clock",
                [0, 0, 0, 0]
            )

            result = central_client.receive_order(
                order_id,
                customer,
                items,
                "Client",
                central_vc
            )

            print("✓ Server-1: Order received")
            print(
                f"  Status: {result['status']}, "
                f"VC: {result['vector_clock']}"
            )

            # =================================================
            # 2. LOAD BALANCING
            # =================================================

            restaurant_name = choose_restaurant()

            print(
                f"✓ Load Balancer: Assigned to "
                f"{restaurant_name}"
            )

            restaurant_load[restaurant_name] += 1

            # =================================================
            # 3. SERVER-1 → RESTAURANT
            # =================================================

            result = central_client.send_order_to_restaurant(
                restaurant_name,
                order_id,
                customer,
                items
            )

            print(
                f"✓ {restaurant_name}: Order received "
                f"from Server-1"
            )

            print(
                f"  Status: {result['status']}, "
                f"VC: {result['vector_clock']}"
            )

            # =================================================
            # 4. RESTAURANT PREPARES ORDER
            # =================================================

            restaurant_client = xmlrpc.client.ServerProxy(
                servers[restaurant_name]["url"],
                allow_none=True
            )

            result = restaurant_client.prepare_order(
                order_id
            )

            print(
                f"✓ {restaurant_name}: Order prepared"
            )

            print(
                f"  Status: {result['status']}, "
                f"VC: {result['vector_clock']}"
            )

            # =================================================
            # 5. RESTAURANT → SERVER-4
            # =================================================

            result = restaurant_client.send_delivery_update(
                "Server-4",
                order_id
            )

            print(
                "✓ Server-4: Delivery accepted"
            )

            print(
                f"  Status: {result['status']}, "
                f"VC: {result['vector_clock']}"
            )

            # =================================================
            # 6. SERVER-4 INTERNAL LOCATION UPDATE
            # =================================================

            delivery_client = xmlrpc.client.ServerProxy(
                servers["Server-4"]["url"],
                allow_none=True
            )

            result = delivery_client.update_location(
                order_id,
                f"En route to {customer}"
            )

            print(
                "✓ Server-4: Location updated"
            )

            print(
                f"  Location: {result['location']}, "
                f"VC: {result['vector_clock']}"
            )

            # =================================================
            # 7. SERVER-4 → SERVER-1
            # =================================================

            result = delivery_client.send_delivery_update(
                "Server-1",
                order_id,
                "DELIVERED",
                f"Address-{customer}"
            )

            print(
                "✓ Server-1: Delivery status received"
            )

            print(
                f"  Status: {result['status']}, "
                f"VC: {result['vector_clock']}"
            )

            successful_orders += 1

        except Exception as e:

            if (
                restaurant_name is not None
                and restaurant_load[restaurant_name] > 0
            ):
                restaurant_load[restaurant_name] -= 1

            print(
                f"✗ Error processing order "
                f"#{order_id}: {e}"
            )

    print(
        f"\nWorkflow complete: "
        f"{successful_orders}/{len(orders)} orders completed."
    )

    return successful_orders == len(orders)


def display_load_balancing_dashboard():
    """
    Display actual restaurant order distribution.

    This is the correct metric for load balancing:
        total = Server-2 assignments + Server-3 assignments
    """
    print("\n" + "=" * 70)
    print("RESTAURANT LOAD BALANCING DASHBOARD")
    print("=" * 70 + "\n")

    total_orders = sum(restaurant_load.values())

    if total_orders == 0:
        print("No restaurant orders assigned yet.")
        print("\nTotal Orders Assigned: 0")
        print(f"Active Servers: {len(active_servers)}")
        print("=" * 70)
        return

    for server_name in ("Server-2", "Server-3"):
        orders = restaurant_load[server_name]
        percentage = (orders / total_orders) * 100

        bar_length = min(50, int(percentage / 2))
        bar = "█" * bar_length + "░" * (50 - bar_length)

        print(
            f"{server_name:12} : {orders:3d} orders "
            f"({percentage:>5.1f}%) {bar}"
        )

    print("\n" + "-" * 70)
    print(f"Total Orders Assigned: {total_orders}")
    print(f"Active Servers: {len(active_servers)}")

    if total_orders > 0:
        difference = abs(
            restaurant_load["Server-2"] - restaurant_load["Server-3"]
        )
        print(f"Load Difference: {difference} order(s)")

    print("=" * 70)


# =====================================================
# SERVER STATISTICS
# =====================================================

def display_server_statistics():
    """Display detailed statistics from each server."""
    print("\n" + "=" * 70)
    print("SERVER STATISTICS")
    print("=" * 70)

    if not active_servers:
        print("\nNo active servers. Run health check first.")
        return

    all_successful = True

    for server_name in active_servers:
        try:
            client = xmlrpc.client.ServerProxy(
                servers[server_name]["url"]
            )
            state = client.get_state()

            if not isinstance(state, dict):
                raise ValueError("Invalid get_state() response")

            stats = state.get("statistics", {})
            print(
                f"\n{server_name} "
                f"({servers[server_name]['name']}):"
            )

            # The current server implementation uses total_requests as
            # an event counter. Label it honestly until server code is changed.
            if "total_requests" in stats:
                print(
                    f"  Server Event/Request Counter: "
                    f"{stats['total_requests']}"
                )

            for key, value in stats.items():
                if key != "total_requests":
                    print(f"  {key}: {value}")

            print(f"  Vector Clock: {state.get('vector_clock')}")

        except Exception as e:
            all_successful = False
            print(
                f"\n✗ {server_name}: Error - {str(e)[:80]}"
            )

    if not all_successful:
        print(
            "\n⚠ Statistics could not be collected from every active server."
        )


# =====================================================
# DEMO
# =====================================================

def run_complete_demo():
    """Run the complete demonstration."""
    print("\n" + "=" * 70)
    print("RUNNING COMPLETE DISTRIBUTED SYSTEM DEMO")
    print("=" * 70)

    if not check_server_health():
        print("\n✗ All four servers must be active.")
        return

    # Reset only client-side restaurant dashboard for a fresh demo.
    restaurant_load["Server-2"] = 0
    restaurant_load["Server-3"] = 0

    if not simulate_food_delivery_workflow():
        print("\n⚠ Workflow did not complete successfully.")
        return

    time.sleep(0.5)

    collect_all_events()
    display_event_log()
    analyze_concurrent_events()
    initiate_snapshot()
    display_server_statistics()
    display_load_balancing_dashboard()


# =====================================================
# MENU
# =====================================================

def display_menu():
    print("\n" + "=" * 70)
    print("MAIN MENU")
    print("=" * 70)
    print("1. Check Server Health")
    print("2. Simulate Food Delivery Workflow")
    print("3. View All Events")
    print("4. Analyze Concurrent Events")
    print("5. Initiate Global Snapshot")
    print("6. View Server Statistics")
    print("7. View Load Balancing Dashboard")
    print("8. Run Complete Demo")
    print("9. Exit")
    print("=" * 70)


print("\n" + "=" * 70)
print(" " * 15 + "DISTRIBUTED FOOD DELIVERY SYSTEM")
print(" " * 15 + "CLIENT COORDINATOR - FIXED")
print("=" * 70)

while True:
    display_menu()

    try:
        choice = input("\nEnter your choice (1-9): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\nShutting down client.")
        break

    if choice == "1":
        check_server_health()

    elif choice == "2":
        simulate_food_delivery_workflow()

    elif choice == "3":
        if not active_servers:
            check_server_health()
        if active_servers:
            collect_all_events()
            display_event_log()

    elif choice == "4":
        if not active_servers:
            check_server_health()
        if active_servers:
            collect_all_events()
            analyze_concurrent_events()

    elif choice == "5":
        if not active_servers:
            check_server_health()
        if active_servers:
            initiate_snapshot()

    elif choice == "6":
        if not active_servers:
            check_server_health()
        if active_servers:
            display_server_statistics()

    elif choice == "7":
        display_load_balancing_dashboard()

    elif choice == "8":
        run_complete_demo()

    elif choice == "9":
        print("\n" + "=" * 70)
        print("SHUTTING DOWN CLIENT")
        print("=" * 70)
        print("\nThank you for using the Distributed Food Delivery System!")
        print("=" * 70 + "\n")
        break

    else:
        print("\n✗ Invalid choice! Please enter 1-9.")