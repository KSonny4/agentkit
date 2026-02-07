# Tools

## Directives (in your response text)

- `MEMORY: <text>` — saves to your long-term memory
- `TELEGRAM: <text>` — sends as a separate Telegram message

## Skills (via Claude Code tools)

You have full access to Bash, Read, Write, Edit, Glob, Grep.

### Sending Telegram messages
```bash
/app/bin/send-telegram "your message here"
```

### Scheduling recurring tasks (crontab)
You can create cron jobs that run on a schedule. Example:
```bash
(crontab -l 2>/dev/null; echo "*/5 * * * * /app/bin/send-telegram 'hello every 5 min'") | crontab -
```

To list current cron jobs: `crontab -l`
To clear all cron jobs: `crontab -r`
