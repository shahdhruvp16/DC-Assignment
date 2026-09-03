# ⚡ QUICK REFERENCE CARD

## 🚀 30-Second Start

```bash
# Window 1
python3 servers/server_1.py

# Window 2
python3 servers/server_2.py

# Window 3
python3 servers/server_3.py

# Window 4
python3 servers/server_4.py

# Window 5
python3 client/client.py
# Choose: 8
```

---

## 🎯 Server Ports & Roles

| Server | Port | Role | Process ID |
|--------|------|------|------------|
| server_1.py | 8000 | Central Order Processor | P0 |
| server_2.py | 8001 | Restaurant 1 | P1 |
| server_3.py | 8002 | Restaurant 2 | P2 |
| server_4.py | 8003 | Delivery Partner | P3 |

---

## 📋 Client Menu Cheat Sheet

```
1 = Check all server health
2 = Process food delivery orders
3 = View event log with vector clocks
4 = Analyze concurrent events
5 = Initiate global snapshot
6 = View server statistics
7 = View load balancing
8 = RUN EVERYTHING (recommended!)
9 = Exit
```

---

## 📊 Vector Clock Format

```
VC[P0, P1, P2, P3]

Example: VC[2, 1, 0, 3]
- P0 did 2 actions
- P1 did 1 action
- P2 did 0 actions
- P3 did 3 actions
```

---

## 🔄 Message Flow Example

```
Order Flow:
P0 receives order (VC[1,0,0,0])
    ↓ SEND with VC[2,0,0,0]
P1 receives (VC[0,0,0,0] + VC[2,0,0,0]) → VC[2,1,0,0]
    ↓ SEND with VC[0,2,0,0]
P3 receives (VC[0,0,0,1] + VC[0,2,0,0]) → VC[0,2,0,2]
```

---

## 📸 Snapshot At A Glance

```
1. P0 initiates → sends markers to P1, P2, P3
2. Each server records its state
3. Each server records in-transit messages
4. All servers verify consistency
5. Global snapshot complete!
```

---

## ✅ What You'll See

### Event Log
```
[HH:MM:SS] P0 [SEND]     VC[2,0,0,0] - Sending order to P1
[HH:MM:SS] P1 [RECEIVE]  VC[2,1,0,0] - Received order from P0
[HH:MM:SS] P1 [INTERNAL] VC[0,2,0,0] - Preparing order
[HH:MM:SS] P3 [RECEIVE]  VC[0,2,0,2] - Received delivery
```

### Concurrent Events
```
P0 VC[1,0,0,0] || P2 VC[0,0,1,0]
(Neither ≤ other = CONCURRENT)
```

### Snapshot Result
```
✓✓✓ SNAPSHOT IS CONSISTENT ✓✓✓
```

---

## 🐛 Emergency Troubleshooting

| Problem | Fix |
|---------|-----|
| Connection refused | Ensure all 4 servers running |
| No events showing | Run option 2 first, then 3 |
| Server down | Restart it (python3 serverX.py) |
| Slow response | Wait a moment, then retry |

---

## 📈 Expected Results

- **Events**: 30-50 per workflow
- **Concurrent Pairs**: 5-20 detected
- **Servers Active**: 4/4 healthy
- **Snapshot Status**: CONSISTENT

---

## 📝 For Your Assignment

Copy-paste these to PDF:
1. Event log (option 3 output)
2. Concurrent events (option 4 output)
3. Snapshot states (option 5 output)
4. Server statistics (option 6 output)
5. Load balancing (option 7 output)

---

## 🎓 Key Concepts

**Vector Clock**: VC increments on any event, takes max on receive
**Concurrent**: Events where VC1 and VC2 neither ≤ other
**Snapshot**: Chandy-Lamport captures consistent global state
**Consistency**: No causality violations in captured state

---

## 🌍 Network Architecture

```
        Client (client.py)
           /  |  \  \
          /   |   \   \
      P0(8000) P1(8001) P2(8002) P3(8003)
    [Central] [Rest1]  [Rest2] [Delivery]
       Order  Prepare  Prepare  Deliver
    Processor Foods   Foods    Orders
```

---

## 💻 Commands Quick List

```bash
# Start all servers
for i in 1 2 3 4; do python3 servers/server_$i.py &; done

# Run client
python3 client/client.py

# View logs
tail -f server_1.log

# Kill all servers
pkill -f "python3 servers"
```

---

## ✨ Pro Tips

1. **Always start servers first** - client needs them running
2. **Use option 8** - automatically does everything
3. **Save client output** - copy to assignment doc
4. **Run multiple times** - concurrent events vary
5. **Watch server terminals** - see real-time events

---

**Made by**: Distributed Computing Group  
**Course**: CCZG 526 - BITS Wilp  
**Date**: September 2026  

---

**Remember**: 5 terminals, run all servers, run client, select 8. Done! 🚀

