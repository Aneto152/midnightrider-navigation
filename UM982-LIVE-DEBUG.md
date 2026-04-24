# UM982 Live Debugging Session

## 🔴 STATUS: MAXIMUM LOGGING ACTIVE

The plugin now logs EVERY step:
- When start() is called
- What config is received
- Validation calls and results
- Commands being sent
- Every single action

## 📍 What Denis Should Do

### Step 1: Open Admin UI
```
http://localhost:3000/admin
```

### Step 2: Find UM982 Plugin
Scroll down to: **"Unicore UM982 GNSS Receiver"**

### Step 3: Try to Save
Click the plugin configuration and click **SAVE**

### Step 4: Tell Me Exactly
**PASTE THE EXACT ERROR MESSAGE YOU SEE:**

Examples:
- "Error: invalid configuration"
- "Error: serialconnection is required"
- "Cannot read property..."
- Empty field instead of /dev/ttyUSB0
- No Save button available
- Any other message

## 🔍 What I'm Monitoring

When Denis takes action, I'll see:
```
[UM982-START] ========== START METHOD CALLED ==========
[UM982-START] Config received: { ... }
[UM982-START] Calling validateConfiguration...
[UM982-START] Validation result: [true/false]
[UM982-START] Serial connection set to: /dev/ttyUSB0
[UM982-START] Clearing error
[UM982-START] Setting status to Starting
[UM982-START] setTimeout fired - sending init commands
[UM982-START] Sending: MODE ROVER UAV
...
```

## 🎯 How We'll Debug

1. Denis tries to SAVE
2. I see the error logs immediately
3. I identify EXACTLY where it fails
4. I fix it with surgical precision
5. We test again

## 📝 Logging Locations

All logs are in:
```bash
journalctl -u signalk -f | grep UM982
```

Or in file:
```bash
tail -100 /tmp/um982-continuous.log
```

## ⚠️ Important

**Tell me the EXACT error message.** Don't summarize - paste exactly what you see.

Examples of what I need:
- ❌ "It doesn't work"
- ✅ "Error: invalid configuration"
- ❌ "The field is empty"
- ✅ "Serial Connection field shows empty when I open config panel"

---

**Ready whenever Denis is!** 🚀
