# Long-Term Memory

This file stores persistent observations and learned facts.


LaunchAgent com.agentkit.joke created at ~/Library/LaunchAgents/com.agentkit.joke.plist — sends a joke via send-telegram every 60s. Stop with `launchctl unload`.

ai_wars deathmatch can stall when OpenClaw agents stop their bot.py early (Agent1 tends to kill its own process claiming resource limits). The deathmatch.sh monitor detects stalls but can't auto-recover — requires manual restart. Multiple deathmatch.sh processes can pile up if launched repeatedly. Fix: kill all, then relaunch one fresh.