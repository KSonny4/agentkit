# Tools

## Directives (in your response text)

- `MEMORY: <text>` — saves to your long-term memory
- `TELEGRAM: <text>` — sends as a separate Telegram message

## Skills (via Claude Code tools)

You have full access to Bash, Read, Write, Edit, Glob, Grep.

### Sending Telegram messages
```bash
bin/send-telegram "your message here"
```

### Scheduling recurring tasks (macOS launchd)
Create a LaunchAgent plist in ~/Library/LaunchAgents/ to run tasks on a schedule.
Example — send a message every 5 minutes:
```bash
cat > ~/Library/LaunchAgents/com.agentkit.myjob.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentkit.myjob</string>
    <key>ProgramArguments</key>
    <array>
        <string>bin/send-telegram</string>
        <string>hello every 5 min</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF
launchctl load ~/Library/LaunchAgents/com.agentkit.myjob.plist
```

To list: `launchctl list | grep agentkit`
To stop: `launchctl unload ~/Library/LaunchAgents/com.agentkit.myjob.plist`
