# Discord Scraper - Rate Limit Solutions

## 🚨 Problem: Rate Limiting

You're experiencing rate limiting because:
1. **Discord aggressively rate limits unauthenticated requests** (50 requests per 10 minutes)
2. **Your IP is flagged** from too many requests
3. **Google blocks automated scraping**
4. **Many scraped invites are expired/invalid**

## ✅ Solutions (Now Implemented!)

### Solution 1: Use a Discord Bot Token (RECOMMENDED)
**Rate Limit: 5000 requests/10min vs 50/10min (100x better!)**

1. Go to https://discord.com/developers/applications
2. Click "New Application" and name it
3. Go to "Bot" section → "Add Bot"
4. Under "Token", click "Reset Token" and copy it
5. Create `discord_token.txt` in the project folder
6. Paste your token into the file
7. Run the scraper and select "Yes" for "Use Discord bot token"

**Example `discord_token.txt`:**
```
YOUR_BOT_TOKEN_HERE
```

⚠️ **NEVER share your token or commit it to git!**

---

### Solution 2: Use Proxies (For Heavy Scraping)
**Rotates IPs to bypass rate limits**

#### Option A: Free Proxies (Slow, Often Dead)
1. Get proxies from:
   - https://www.proxyscrape.com/
   - https://free-proxy-list.net/
   - https://www.proxy-list.download/

2. Create `proxies.txt` with one proxy per line:
```
http://proxy1.example.com:8080
http://user:pass@proxy2.example.com:3128
socks5://proxy3.example.com:1080
```

3. Install proxy support:
```bash
npm install https-proxy-agent
```

4. Run scraper and select "Yes" for "Use proxy rotation"

#### Option B: Paid Proxies (Fast, Reliable) - RECOMMENDED
**Best providers:**
- **BrightData** (formerly Luminati) - Most reliable
- **Smartproxy** - Good price/quality
- **Oxylabs** - Enterprise-grade
- **IPRoyal** - Budget-friendly

**Cost:** $50-500/month depending on volume

---

### Solution 3: Widget API Alternative
**Different rate limit pool, sometimes works better**

1. Run the scraper
2. Select "Yes" for "Use Widget API"
3. This uses Discord's widget endpoint which has separate rate limits

---

### Solution 4: Use a VPS (Virtual Private Server)
**Fresh IP address, better for long-running scrapes**

#### Recommended VPS Providers:
- **DigitalOcean** ($6/month) - Easy setup
- **Vultr** ($5/month) - Fast
- **Linode** ($5/month) - Reliable
- **AWS Lightsail** ($3.50/month) - Cheap

#### Setup on VPS:
```bash
# SSH into your VPS
ssh user@your-vps-ip

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Clone/upload your project
# Install dependencies
npm install

# Run the scraper
node server_scraper.js
```

**Benefits:**
- ✅ Fresh IP not flagged by Discord
- ✅ Can run 24/7 without your computer
- ✅ Often better network speeds
- ✅ Can combine with proxies for even better results

---

### Solution 5: Optimize Scraper Settings
**Reduce rate limit hits**

1. **Increase request delay:** 800-2000ms instead of 400ms
2. **Lower concurrent workers:** 1-3 instead of 5-20
3. **Enable member filtering:** Skip low-member servers early
4. **Disable web scraping:** Many sources have dead invites anyway

---

## 🎯 Recommended Setup (Best Results)

### For Small Scale (< 1000 invites):
1. ✅ Use Discord Bot Token
2. ✅ Request delay: 800ms
3. ✅ Concurrent workers: 3
4. ✅ No proxies needed

### For Medium Scale (1000-10000 invites):
1. ✅ Use Discord Bot Token
2. ✅ Use VPS
3. ✅ Request delay: 600ms
4. ✅ Concurrent workers: 5

### For Large Scale (10000+ invites):
1. ✅ Use Discord Bot Token
2. ✅ Use VPS + Residential Proxies
3. ✅ Request delay: 400ms
4. ✅ Concurrent workers: 10-20
5. ✅ Multiple bot tokens rotating

---

## 📊 Why Invites Keep Being Invalid

**Common reasons:**
1. **Invite expired** - Most public invites expire after 7 days
2. **Server deleted** - Server no longer exists
3. **Invite revoked** - Owner manually disabled it
4. **One-time use** - Already used once
5. **Web scrapers collect old data** - Invite sites aren't updated

**Solution:** Focus on sources with fresh invites (disboard.org, top.gg)

---

## 🔧 Troubleshooting

### "Still getting rate limited with bot token"
- Make sure token is valid (test in Discord developer portal)
- Check you're not hitting daily limits (5000 req/10min)
- Try enabling Widget API mode

### "Proxies not working"
- Install: `npm install https-proxy-agent`
- Test proxies manually first
- Free proxies often don't work - use paid ones
- Check proxy format is correct

### "Browser works but scraper doesn't"
- Browser uses your cookies/session
- Scraper uses fresh requests
- Discord detects and limits automation
- **Solution:** Use bot token authentication

### "Should I use a VPS?"
**Yes, if:**
- ✅ Your home IP is flagged/rate limited
- ✅ You need to scrape 1000+ invites
- ✅ You want to run 24/7
- ✅ You're combining with proxies

**No, if:**
- ❌ Just testing/learning
- ❌ Only need < 500 invites
- ❌ Using bot token works fine

---

## 💡 Pro Tips

1. **Start small:** Test with 50-100 invites first
2. **Use bot token first:** Try this before buying proxies/VPS
3. **Monitor stats:** Watch success rate - should be 20-40%
4. **Filter early:** Use min members filter to skip dead servers
5. **Resume capability:** Scraper auto-saves - can restart anytime
6. **Combine methods:** Bot token + VPS + proxies = best results

---

## 📝 Quick Start Guide

### Minimal Setup (No Extra Cost):
```bash
# 1. Create Discord bot and get token
# 2. Save token to discord_token.txt
# 3. Run scraper
node server_scraper.js

# 4. Select these options:
# - Use Discord bot token: Yes
# - Request delay: 800 (Safe)
# - Concurrent workers: 3 (Safe)
# - Min members: 10
```

### Maximum Performance Setup:
```bash
# 1. Get VPS ($5-10/month)
# 2. Get residential proxies ($50-100/month)
# 3. Create 2-3 Discord bots for rotation
# 4. Save tokens and proxies
npm install https-proxy-agent
node server_scraper.js

# 5. Select these options:
# - Use proxies: Yes
# - Use Discord bot token: Yes
# - Request delay: 400 (Fast)
# - Concurrent workers: 20 (Very Fast)
# - Min members: 50
```

---

## 🆘 Still Having Issues?

Common fixes:
- Wait 10-15 minutes if rate limited
- Restart with different IP (VPN/mobile hotspot)
- Verify bot token is valid
- Check Discord API status: https://discordstatus.com/
- Try Widget API mode
- Use higher request delays (1000-2000ms)

The bot token alone should fix 90% of rate limit issues!
