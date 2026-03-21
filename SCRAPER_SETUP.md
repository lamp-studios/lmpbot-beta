# Discord Server Scraper - Quick Setup Guide

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Dependencies
```bash
# Install optional proxy support (recommended)
npm install https-proxy-agent

# Or just update all dependencies
npm install
```

### Step 2: Setup Discord Bot Token (RECOMMENDED)
**This solves 90% of rate limit issues!**

1. Visit: https://discord.com/developers/applications
2. Click "New Application" → Name it "Invite Scraper"
3. Go to "Bot" section → Click "Add Bot"
4. Click "Reset Token" → Copy the token
5. Create `discord_token.txt` in this folder
6. Paste your token into the file (one line, no quotes)

**Example `discord_token.txt`:**
```
YOUR_BOT_TOKEN_HERE
```

### Step 3: Run the Scraper
```bash
node server_scraper.js

# Or use npm script
npm run scrape
```

### Step 4: Configure Settings
When prompted, select:
- **Max invites:** 5000 (or your desired amount)
- **Request delay:** 800 (Safe) - prevents rate limiting
- **Enable web scraping:** Yes
- **Test vanity URLs:** Yes
- **Test random codes:** No (unless you want to try)
- **Auto-save interval:** 10
- **Concurrent workers:** 3 (Safe) - higher = faster but more rate limits
- **Min members:** 10 (or your preference)
- **Resume from checkpoint:** Yes
- **Use proxies:** No (unless you have proxies.txt setup)
- **Use Discord token:** Yes (if you created discord_token.txt)
- **Use Widget API:** No (try if regular API gets rate limited)
- **Show debug:** No (unless troubleshooting)

## 📊 Output Files

The scraper creates 4 files in the `slash/` folder:

1. **invites.json** - Array of invite codes
```json
[
  "discord",
  "minecraft",
  "fortnite"
]
```

2. **invites_detailed.json** - Full server details
```json
[
  {
    "code": "discord",
    "guildName": "Discord Official",
    "guildId": "123456789",
    "memberCount": 1000000,
    "features": ["COMMUNITY", "VERIFIED"],
    "description": "Official Discord server",
    "banner": "...",
    "icon": "..."
  }
]
```

3. **invites.csv** - Spreadsheet format
```csv
Code,Guild Name,Guild ID,Members,Features,Description,Invite URL
discord,"Discord Official",123456789,1000000,"COMMUNITY, VERIFIED","Official Discord server",https://discord.gg/discord
```

4. **scraper_checkpoint.json** - Resume file (auto-deleted on completion)

## 🔧 Optional: Setup Proxies (For Heavy Scraping)

### Option 1: Free Proxies
1. Get proxies from https://www.proxyscrape.com/
2. Create `proxies.txt` in this folder
3. Add one proxy per line:
```
http://proxy1.example.com:8080
http://user:pass@proxy2.example.com:3128
```
4. Run scraper and select "Yes" for proxies

### Option 2: Paid Proxies (Better Results)
- **Smartproxy:** ~$50/month
- **BrightData:** ~$100/month
- **IPRoyal:** ~$30/month

## 🎯 Using with find_tags.js Command

After scraping, use the Discord bot command to filter servers with guild tags:

```
/find_tags channel:#your-channel min_members:50
```

This will:
- Read invites.json
- Check each server for guild tags
- Send embeds to your channel
- Save results to tags.json

## 💡 Tips for Best Results

### Avoid Rate Limits:
1. ✅ Use Discord bot token
2. ✅ Set request delay to 800-1200ms
3. ✅ Use 3-5 concurrent workers
4. ✅ Let it run overnight for large batches

### Get More Valid Invites:
1. ✅ Enable web scraping (disboard.org, top.gg)
2. ✅ Enable vanity testing (common words)
3. ✅ Set min members filter (skip dead servers)
4. ✅ Check success rate - should be 20-40%

### Speed Up Scraping:
1. ⚡ Use Discord bot token
2. ⚡ Increase concurrent workers to 10-20
3. ⚡ Lower request delay to 400-600ms
4. ⚡ Use proxies to rotate IPs
5. ⚡ Run on a VPS

## 🆘 Troubleshooting

### "Rate limited even with bot token"
- Wait 10 minutes and try again
- Increase request delay to 1200-2000ms
- Lower concurrent workers to 1-2
- Enable Widget API mode

### "Most invites are invalid"
- This is normal - public invites expire quickly
- Success rate should be 20-40%
- Focus on min members filter
- Try different scraping sources

### "Scraper crashes or stops"
- Enable resume from checkpoint
- Run will auto-save progress
- Restart and it continues where it left off

### "Want to run on VPS"
See: RATE_LIMIT_GUIDE.md for VPS setup instructions

## 📝 Example Run

```bash
$ node server_scraper.js

╔═══════════════════════════════════════════════════════╗
║       Discord Server Scraper v4.0 - Running          ║
╚═══════════════════════════════════════════════════════╝

🎯 Target: 5000 invites
📁 Output: D:\! Projects\lmpbot-beta\slash\invites.json
💾 Auto-save: Every 10 invites
⚡ Workers: 3 concurrent
👥 Min Members: 10
🐛 Debug: Disabled

🔑 Loaded Discord bot token
📂 Starting fresh

🌐 Web Scraping Phase
📋 [1/8] tags.mgcounts.com
  ✓ code1 - Server Name (1234 members)
  ✓ code2 - Another Server (567 members)
  Progress: [████████████░░░░░░░░] 40.2% | Found: 201/5000 | Time: 15.3m | ETA: 22m
  ✓ Found 42 new invites

... (continues scraping) ...

✨ Scraping completed!

╔═══════════════════════════════════════════════════════╗
║                      Statistics                       ║
╠═══════════════════════════════════════════════════════╣
║  Checked:     1234                                    ║
║  Valid:       456                                     ║
║  Failed:      778                                     ║
║  Expired:     234                                     ║
║  Filtered:    89                                      ║
║  Rate Limited:0                                       ║
║  From Scrape: 345                                     ║
║  Duplicates:  12                                      ║
║  Success Rate:36.98%                                  ║
║  Total Unique:456                                     ║
║  Time Elapsed:45.23 min                               ║
║  Rate:        10.08 invites/min                       ║
╚═══════════════════════════════════════════════════════╝

📊 Files saved:
  - D:\! Projects\lmpbot-beta\slash\invites.json
  - D:\! Projects\lmpbot-beta\slash\invites_detailed.json
  - D:\! Projects\lmpbot-beta\slash\invites.csv
```

## 🔗 Related Files

- **RATE_LIMIT_GUIDE.md** - Complete guide to fixing rate limit issues
- **proxies.txt.example** - Example proxy configuration
- **discord_token.txt.example** - Example token file
- **server_scraper.js** - Main scraper script
- **slash/find_tags.js** - Discord command to filter guild tags

---

## Need Help?

1. Read RATE_LIMIT_GUIDE.md for rate limit solutions
2. Enable debug mode to see detailed logs
3. Check Discord API status: https://discordstatus.com/
4. Make sure bot token is valid
5. Try Widget API mode if regular API fails

**Most common fix:** Just add your Discord bot token to `discord_token.txt`!
