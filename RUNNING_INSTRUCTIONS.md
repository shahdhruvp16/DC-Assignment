# 🚀 DISTRIBUTED FOOD DELIVERY SYSTEM - RUNNING INSTRUCTIONS

## Project Structure

```
distributed_food_delivery/
├── servers/
│   ├── server_1.py          (Port 8000) - Central Order Processor
│   ├── server_2.py          (Port 8001) - Restaurant 1
│   ├── server_3.py          (Port 8002) - Restaurant 2
│   └── server_4.py          (Port 8003) - Delivery Partner
├── client/
│   └── client.py            - Client Coordinator
├── logs/
│   └── (auto-generated logs)
└── RUNNING_INSTRUCTIONS.md  (This file)
```

---

## 📋 Prerequisites

- **Python 3.7+**
- **Linux/Mac/Windows (with terminal)**
- **4 terminal windows** (one for each server + one for client)

Check Python version:
```bash
python3 --version
```

---

## 🎯 HOW TO RUN (3 Simple Steps)

### Step 1: Open 4 Terminal Windows

You need **4 separate terminal tabs/windows** because each server runs continuously.

### Step 2: Start All 4 Servers (in separate terminals)

**Terminal 1 - Server 1 (Central Order Processor)**
```bash
cd /home/claude/distributed_food_delivery/servers
python3 server_1.py
```
Expected output:
```
==================================================
   CENTRAL ORDER PROCESSOR (Server 1)
==================================================

✓ Server 1 running on port 8000...

Registered Functions:
  ✓ health()
  ✓ receive_order(order_id, customer_name, items, from_server)
  ...

Waiting for client requests...
```

**Terminal 2 - Server 2 (Restaurant 1)**
```bash
cd /home/claude/distributed_food_delivery/servers
python3 server_2.py
```

**Terminal 3 - Server 3 (Restaurant 2)**
```bash
cd /home/claude/distributed_food_delivery/servers
python3 server_3.py
```

**Terminal 4 - Server 4 (Delivery Partner)**
```bash
cd /home/claude/distributed_food_delivery/servers
python3 server_4.py
```

### Step 3: Run Client in 5th Terminal/Window

```bash
cd /home/claude/distributed_food_delivery/client
python3 client.py
```

---

## 🎮 CLIENT MENU OPTIONS

Once client runs, you'll see menu:

```
======================================================================
MAIN MENU
======================================================================
1. Check Server Health
2. Simulate Food Delivery Workflow
3. View All Events
4. Analyze Concurrent Events
5. Initiate Global Snapshot
6. View Server Statistics
7. View Load Balancing Dashboard
8. Run Complete Demo
9. Exit
======================================================================
```

### Option 1: Check Server Health
```
Select: 1

Output:
✓ Server-1 (Central Order Processor): Server 1 is Healthy ✓
✓ Server-2 (Restaurant 1): Server 2 is Healthy ✓
✓ Server-3 (Restaurant 2): Server 3 is Healthy ✓
✓ Server-4 (Delivery Partner): Server 4 is Healthy ✓
```

### Option 2: Simulate Food Delivery Workflow
```
Select: 2

Creates 3 orders and processes them through all servers:
Order #101 (Alice) → Central → Restaurant → Delivery → Confirmed
Order #102 (Bob)   → Central → Restaurant → Delivery → Confirmed
Order #103 (Charlie) → Central → Restaurant → Delivery → Confirmed
```

### Option 3: View All Events
```
Select: 3

Shows complete event log with Vector Clocks:
1.   [HH:MM:SS] P0-Server1   [INTERNAL] VC[1,0,0,0] - Health check performed
2.   [HH:MM:SS] P1-Server2   [RECEIVE]  VC[1,1,0,0] - Order #101 from Server-1
3.   [HH:MM:SS] P1-Server2   [INTERNAL] VC[0,2,0,0] - Preparing order #101
...
```

### Option 4: Analyze Concurrent Events
```
Select: 4

Shows pairs of concurrent events (events that don't causally relate):
Concurrent Events Found: N

1. P1 VC[1,1,0,0] || P3 VC[0,0,0,1]
2. P0 VC[1,0,0,0] || P2 VC[0,0,1,0]
...
```

### Option 5: Initiate Global Snapshot
```
Select: 5

Triggers Chandy-Lamport snapshot:
✓ Snapshot initiated by P0-Server1
  Snapshot ID: 1
  Process State: {role: 'Central Order Processor', ...}
  Vector Clock: [5, 3, 2, 4]
  Events Logged: 23
  
COLLECTING STATE FROM ALL SERVERS
✓ Server-1: State collected, VC: [5,3,2,4]
✓ Server-2: State collected, VC: [1,5,0,0]
✓ Server-3: State collected, VC: [0,0,4,1]
✓ Server-4: State collected, VC: [2,0,1,6]

✓✓✓ SNAPSHOT IS CONSISTENT ✓✓✓
```

### Option 6: View Server Statistics
```
Select: 6

Shows detailed statistics from each server:
Server-1 (Central Order Processor):
  Total Requests: 15
  Orders Processed: 5
  Events Logged: 8
  Vector Clock: [5,3,2,4]

Server-2 (Restaurant 1):
  Total Requests: 12
  Orders Received: 3
  Orders Prepared: 3
  Events Logged: 7
  Vector Clock: [1,5,0,0]
...
```

### Option 7: View Load Balancing Dashboard
```
Select: 7

Shows request distribution:
Server-1      :   5 requests ( 25.0%) ██████████████░░░░░░░░░░░░░░░░░░
Server-2      :   4 requests ( 20.0%) ██████████░░░░░░░░░░░░░░░░░░░░░░
Server-3      :   5 requests ( 25.0%) ██████████████░░░░░░░░░░░░░░░░░░
Server-4      :   6 requests ( 30.0%) ███████████████░░░░░░░░░░░░░░░░░

Total Requests: 20
Active Servers: 4
```

### Option 8: Run Complete Demo
```
Select: 8

Runs everything automatically:
1. Checks all server health
2. Processes 3 food delivery orders
3. Collects all events
4. Displays complete event log
5. Analyzes concurrent events
6. Initiates global snapshot
7. Shows server statistics
8. Displays load balancing

This is the RECOMMENDED option for seeing everything!
```

### Option 9: Exit
```
Select: 9

Gracefully shuts down client
(Servers continue running - Ctrl+C to stop them individually)
```

---

## 🔍 WHAT'S HAPPENING UNDER THE HOOD

### Vector Clocks in Action

Each server maintains a vector clock [P0, P1, P2, P3]:

```
Event 1 at P0: VC[0,0,0,0] → INTERNAL → VC[1,0,0,0]
Event 2 at P1: VC[0,0,0,0] → RECEIVE from P0 → VC[1,1,0,0]
Event 3 at P0: VC[1,0,0,0] → SEND to P1 → VC[2,0,0,0]
Event 4 at P2: VC[0,0,0,0] → INTERNAL → VC[0,0,1,0]

Event 3 & 4 are CONCURRENT (neither ≤ other)
```

### Message Flow with Timestamps

```
P0 (Central) sends ORDER to P1 (Restaurant)
├─ P0: VC[1,0,0,0] → SEND → VC[2,0,0,0]
├─ MESSAGE carries: VC[2,0,0,0]
└─ P1: VC[0,0,0,0] → RECEIVE VC[2,0,0,0] → VC[2,1,0,0]

P1 sends UPDATE to P3 (Delivery)
├─ P1: VC[0,2,0,0] → SEND → VC[0,3,0,0]
├─ MESSAGE carries: VC[0,3,0,0]
└─ P3: VC[0,0,0,1] → RECEIVE VC[0,3,0,0] → VC[0,3,0,2]
```

### Snapshot Process (Chandy-Lamport)

```
Step 1: P0 initiates snapshot
├─ Records own state
└─ Sends marker to P1, P2, P3

Step 2: P1, P2, P3 receive marker
├─ Record their states
└─ Forward marker to others

Step 3: All servers aware of snapshot
├─ Collect process states
├─ Record in-transit messages
└─ Verify consistency

Result: Consistent global state captured!
```

---

## 📊 UNDERSTANDING OUTPUT

### Server Terminal Output

When a request comes in, server logs:
```
[HH:MM:SS] P1 [RECEIVE] VC[1,1,0,0] - Order #101 from Server-1: Alice ordered Pizza + Coke
[HH:MM:SS] P1 [INTERNAL] VC[0,2,0,0] - Preparing order #101 in kitchen
[HH:MM:SS] P1 [SEND] VC[0,3,0,0] - Sending order #101 to Server-4 for delivery
```

**Interpretation**:
- `[HH:MM:SS]`: Timestamp when event logged
- `P1`: Process ID (Server 2 in this case)
- `[RECEIVE/INTERNAL/SEND]`: Event type
- `VC[1,1,0,0]`: Vector clock (P0 did 1, P1 did 1, P2 did 0, P3 did 0)
- `Description`: What happened

### Client Terminal Output

Shows:
- Server health status
- Event log with vector clocks
- Concurrent event pairs
- Snapshot states
- Load balancing statistics

---

## ⚙️ SYSTEM COMPONENTS

### P0 - Server 1: Central Order Processor
- **Role**: Receives orders, coordinates between restaurants and delivery
- **Port**: 8000
- **Operations**: receive_order, send_order_to_restaurant, receive_delivery_status
- **State**: orders_received, orders_processed, status

### P1 - Server 2: Restaurant 1
- **Role**: Prepares food orders
- **Port**: 8001
- **Operations**: receive_order, prepare_order, send_delivery_update
- **State**: orders_received, orders_prepared, kitchen_status

### P2 - Server 3: Restaurant 2
- **Role**: Prepares food orders (alternate)
- **Port**: 8002
- **Operations**: receive_order, prepare_order, send_delivery_update
- **State**: orders_received, orders_prepared, kitchen_status

### P3 - Server 4: Delivery Partner
- **Role**: Manages deliveries
- **Port**: 8003
- **Operations**: accept_delivery, update_location, confirm_delivery
- **State**: deliveries_completed, current_location, vehicle_status

---

## 🧪 TESTING SCENARIOS

### Scenario 1: Normal Operations
```
1. Run all 4 servers
2. Select Option 2 (Simulate Workflow)
3. Check menu option 3 to see events
4. Observe vector clock progression
```

### Scenario 2: Health Monitoring
```
1. Stop one server (Ctrl+C in its terminal)
2. Client option 1 (Health Check) will show one server DOWN
3. Operations still work with remaining servers
4. Restart the server to bring it back
```

### Scenario 3: Concurrent Events
```
1. Run all servers
2. Select Option 2 multiple times quickly
3. Select Option 4 (Analyze Concurrent)
4. See multiple concurrent event pairs
```

### Scenario 4: Global Snapshot
```
1. Run all servers
2. Select Option 2 (Simulate)
3. Select Option 5 (Snapshot)
4. Observe consistent global state capture
5. Verify no causality violations
```

---

## 📈 PERFORMANCE EXPECTATIONS

### Event Log Size
- Each order generates ~5-10 events (send, receive, internal)
- 3 orders = ~15-30 events
- Complete demo = ~40-50 events

### Concurrent Events
- With 4 processes running simultaneously
- Typically 5-20 concurrent event pairs per workflow
- More with heavier workload

### Snapshot Time
- Snapshot initiation: ~0.5-1 second
- State collection: ~1-2 seconds
- Consistency verification: immediate

---

## 🐛 TROUBLESHOOTING

### "Connection refused" Error
```
Error: Connection refused on port 8000

Solution:
- Make sure Server 1 is running in a separate terminal
- Check if port 8000 is available (netstat -a)
- Wait a moment for server to start up
```

### "No active servers available"
```
Solution:
- Ensure all 4 server scripts are running
- Check that all terminals show "Waiting for client requests..."
- Verify no firewall blocking localhost connections
```

### Client shows "Server DOWN"
```
Possible causes:
1. Server crashed or Ctrl+C was pressed
2. Server is slow to respond (network lag)
3. Firewall blocking connection

Solution:
- Restart the affected server
- Increase timeout value in client.py if running on slow system
```

### Events not showing up
```
Solution:
1. Make sure you ran Option 2 (Simulate Workflow) first
2. Run Option 3 to collect events before viewing
3. Check server terminals for any error messages
```

---

## 📝 HOW TO GATHER OUTPUT FOR ASSIGNMENT

### Capture All Output to File

**For servers** (in each server terminal):
```bash
python3 server_1.py | tee server_1.log
python3 server_2.py | tee server_2.log
python3 server_3.py | tee server_3.log
python3 server_4.py | tee server_4.log
```

**For client** (in client terminal):
```bash
python3 client.py | tee client.log
```

Then select Option 8 (Complete Demo) to generate all output.

### Files Saved:
- `server_1.log` - Central Processor events
- `server_2.log` - Restaurant 1 events
- `server_3.log` - Restaurant 2 events
- `server_4.log` - Delivery Partner events
- `client.log` - Client operations and analysis

### Copy to Assignment Directory:
```bash
cp *.log /path/to/assignment/folder/
```

---

## 📚 WHAT TO DOCUMENT FOR YOUR PDF

1. **System Architecture**
   - 4 independent processes (servers)
   - XML-RPC communication
   - Vector clock on each process

2. **Event Log**
   - Copy from `client.log` option 3 output
   - Show at least 20 events with vector clocks
   - Highlight different event types (SEND, RECEIVE, INTERNAL)

3. **Concurrent Events**
   - Copy from `client.log` option 4 output
   - Show at least 5 concurrent event pairs
   - Explain why they are concurrent

4. **Global Snapshot**
   - Copy from `client.log` option 5 output
   - Show process states at snapshot time
   - Show vector clocks
   - Verify consistency

5. **Server Statistics**
   - Copy from `client.log` option 6 output
   - Show requests per server
   - Show events logged per server

6. **Load Balancing**
   - Copy from `client.log` option 7 output
   - Show distribution across servers

---

## ✅ VERIFICATION CHECKLIST

After running system:
- [ ] All 4 servers start successfully
- [ ] Client connects to all servers
- [ ] Health check shows all servers HEALTHY
- [ ] Workflow processes orders correctly
- [ ] Event log shows 30+ events
- [ ] Concurrent events detected (5+ pairs)
- [ ] Snapshot initiates successfully
- [ ] Snapshot shows CONSISTENT
- [ ] Server statistics show activity
- [ ] Load balancing dashboard populates

---

## 🎓 KEY LEARNING POINTS

### Vector Clocks
- Each server increments own counter on action
- Takes max with received counters
- Enables ordering without global clock

### Concurrent Events
- Events where neither causally precedes other
- Identified by comparing vector clocks
- Neither ≤ the other = CONCURRENT

### Snapshot Algorithm
- Non-blocking global state capture
- Uses marker messages
- Ensures consistency

### Distributed Communication
- XML-RPC enables remote function calls
- Messages carry vector clocks
- Enables causal ordering of operations

---

## 💡 QUICK START (FOR THE IMPATIENT)

```bash
# Terminal 1
python3 servers/server_1.py

# Terminal 2
python3 servers/server_2.py

# Terminal 3
python3 servers/server_3.py

# Terminal 4
python3 servers/server_4.py

# Terminal 5
python3 client/client.py
# Then select: 8 (Complete Demo)
```

Done! You'll see everything working in ~30 seconds.

---

**Version**: 1.0  
**Last Updated**: September 2026  
**Status**: Ready for Submission

Good luck! 🚀

