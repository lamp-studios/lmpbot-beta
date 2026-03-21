const https = require('https');
const http = require('http');
const fs = require('fs').promises;
const path = require('path');
const readline = require('readline');

// Optional proxy support
let HttpsProxyAgent;
try {
    HttpsProxyAgent = require('https-proxy-agent').HttpsProxyAgent;
} catch (e) {
    // Proxy support not available
}

// Configuration
const CONFIG = {
    outputFile: path.join(__dirname, 'slash', 'invites.json'),
    checkpointFile: path.join(__dirname, 'slash', 'scraper_checkpoint.json'),
    proxyFile: path.join(__dirname, 'proxies.txt'),
    tokenFile: path.join(__dirname, 'discord_token.txt'),
    maxInvites: 5000,
    requestDelay: 400,
    timeout: 10000,
    retryAttempts: 3,
    retryDelay: 1500,
    sourceTimeout: 60000,
    autoSaveInterval: 10,
    showDebug: false,
    concurrentRequests: 5, // Process multiple invites concurrently
    minMemberCount: 0, // Minimum members filter
    useProxies: false,
    useDiscordToken: false,
    useWidgetAPI: false, // Alternative API with different rate limits

    inviteLength: [5, 6, 7, 8, 10],
    charactersPool: 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',

    // User agents to rotate
    userAgents: [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    ],

    commonWords: [
        'gaming', 'chat', 'community', 'friends', 'hangout', 'chill',
        'anime', 'memes', 'music', 'art', 'coding', 'dev', 'support',
        'official', 'main', 'discord', 'server', 'lounge', 'hub',
        'social', 'fun', 'active', 'game', 'minecraft', 'roblox',
        'fortnite', 'valorant', 'league', 'csgo', 'gta', 'rpg',
        'nft', 'crypto', 'trading', 'stocks', 'invest', 'money',
        'study', 'homework', 'college', 'university', 'school',
        'dating', 'meet', 'talk', 'voice', 'call', 'stream',
        'twitch', 'youtube', 'tiktok', 'instagram', 'twitter',
        'lane', 'clashofclans', 'guild', 'hangout',
        'youtuber', 'ai', 'cats', 'cat', 'tag', 'tags', 'bot', 'bots'
    ]
};

class InteractiveMenu {
    constructor() {
        this.settings = {
            maxInvites: 5000,
            requestDelay: 400,
            concurrentRequests: 5,
            minMemberCount: 0,
            enableWebScraping: true,
            enableVanityTesting: true,
            enableRandomTesting: false,
            autoSaveInterval: 10,
            showDebug: false,
            resumeFromCheckpoint: true,
            useProxies: false,
            useDiscordToken: false,
            useWidgetAPI: false,
            skipVerification: false
        };
    }

    async show() {
        console.clear();
        console.log('\x1b[36m╔═══════════════════════════════════════════════════════╗\x1b[0m');
        console.log('\x1b[36m║       Discord Server Scraper v4.0 - Config           ║\x1b[0m');
        console.log('\x1b[36m╚═══════════════════════════════════════════════════════╝\x1b[0m\n');

        const questions = [
            {
                key: 'maxInvites',
                question: '\x1b[33m❓ Maximum invites to collect\x1b[0m',
                options: ['50', '100', '500', '1000', '5000', '10000'],
                default: 4
            },
            {
                key: 'requestDelay',
                question: '\x1b[33m❓ Request delay (ms)\x1b[0m',
                options: ['600 (Fast)', '800 (Normal)', '1200 (Safe)', '2000 (Very Safe)'],
                default: 2
            },
            {
                key: 'enableWebScraping',
                question: '\x1b[33m❓ Enable web scraping\x1b[0m',
                options: ['Yes', 'No'],
                default: 0
            },
            {
                key: 'enableVanityTesting',
                question: '\x1b[33m❓ Test vanity URLs\x1b[0m',
                options: ['Yes', 'No'],
                default: 0
            },
            {
                key: 'enableRandomTesting',
                question: '\x1b[33m❓ Test random invite codes\x1b[0m',
                options: ['Yes', 'No'],
                default: 1
            },
            {
                key: 'autoSaveInterval',
                question: '\x1b[33m❓ Auto-save every N invites\x1b[0m',
                options: ['5', '10', '25', '50'],
                default: 1
            },
            {
                key: 'concurrentRequests',
                question: '\x1b[33m❓ Concurrent request workers\x1b[0m',
                options: ['1 (Slow)', '3 (Safe)', '5 (Normal)', '10 (Fast)', '20 (Very Fast)'],
                default: 2
            },
            {
                key: 'minMemberCount',
                question: '\x1b[33m❓ Minimum server members\x1b[0m',
                options: ['0 (All)', '10', '50', '100', '500', '1000'],
                default: 0
            },
            {
                key: 'resumeFromCheckpoint',
                question: '\x1b[33m❓ Resume from previous session\x1b[0m',
                options: ['Yes', 'No'],
                default: 0
            },
            {
                key: 'skipVerification',
                question: '\x1b[33m❓ Skip verification (collect codes only, verify later)\x1b[0m',
                options: ['Yes (Fast, recommended)', 'No (Slow, verify now)'],
                default: 0
            },
            {
                key: 'useProxies',
                question: '\x1b[33m❓ Use proxy rotation (proxies.txt)\x1b[0m',
                options: ['Yes', 'No'],
                default: 1
            },
            {
                key: 'useDiscordToken',
                question: '\x1b[33m❓ Use Discord bot token (higher limits)\x1b[0m',
                options: ['Yes', 'No'],
                default: 1
            },
            {
                key: 'useWidgetAPI',
                question: '\x1b[33m❓ Use Widget API (alternative method)\x1b[0m',
                options: ['Yes', 'No'],
                default: 1
            },
            {
                key: 'showDebug',
                question: '\x1b[33m❓ Show debug info\x1b[0m',
                options: ['Yes', 'No'],
                default: 1
            }
        ];

        for (const q of questions) {
            const answer = await this.askQuestion(q.question, q.options, q.default);

            if (q.key === 'maxInvites') {
                this.settings[q.key] = parseInt(q.options[answer]);
            } else if (q.key === 'requestDelay') {
                this.settings[q.key] = parseInt(q.options[answer].split(' ')[0]);
            } else if (q.key === 'autoSaveInterval') {
                this.settings[q.key] = parseInt(q.options[answer]);
            } else if (q.key === 'concurrentRequests') {
                this.settings[q.key] = parseInt(q.options[answer].split(' ')[0]);
            } else if (q.key === 'minMemberCount') {
                this.settings[q.key] = parseInt(q.options[answer].split(' ')[0]);
            } else if (['showDebug', 'resumeFromCheckpoint', 'useProxies', 'useDiscordToken', 'useWidgetAPI', 'skipVerification'].includes(q.key)) {
                this.settings[q.key] = answer === 0;
            } else {
                this.settings[q.key] = answer === 0;
            }
        }

        if (process.stdin.isTTY) {
            process.stdin.setRawMode(false);
        }
        process.stdin.pause();

        console.log('\n\x1b[32m✓ Configuration complete!\x1b[0m');
        await this.delay(1000);
        return this.settings;
    }

    askQuestion(question, options, defaultIndex = 0) {
        return new Promise((resolve) => {
            let selectedIndex = defaultIndex;

            const renderMenu = () => {
                readline.clearLine(process.stdout, 0);
                readline.cursorTo(process.stdout, 0);

                console.log(`\n${question}`);
                options.forEach((option, index) => {
                    if (index === selectedIndex) {
                        console.log(`\x1b[42m\x1b[30m → ${option} \x1b[0m`);
                    } else {
                        console.log(`   ${option}`);
                    }
                });
                console.log('\n\x1b[90m(Use ↑/↓ arrow keys, press Enter to select)\x1b[0m');
            };

            renderMenu();

            if (!process.stdin.isRaw && process.stdin.isTTY) {
                readline.emitKeypressEvents(process.stdin);
                process.stdin.setRawMode(true);
            }

            if (process.stdin.isPaused()) {
                process.stdin.resume();
            }

            const onKeypress = (_str, key) => {
                if (!key) return;

                if (key.name === 'up') {
                    selectedIndex = (selectedIndex - 1 + options.length) % options.length;
                    console.clear();
                    console.log('\x1b[36m╔═══════════════════════════════════════════════════════╗\x1b[0m');
                    console.log('\x1b[36m║       Discord Server Scraper v4.0 - Config           ║\x1b[0m');
                    console.log('\x1b[36m╚═══════════════════════════════════════════════════════╝\x1b[0m');
                    renderMenu();
                } else if (key.name === 'down') {
                    selectedIndex = (selectedIndex + 1) % options.length;
                    console.clear();
                    console.log('\x1b[36m╔═══════════════════════════════════════════════════════╗\x1b[0m');
                    console.log('\x1b[36m║       Discord Server Scraper v4.0 - Config           ║\x1b[0m');
                    console.log('\x1b[36m╚═══════════════════════════════════════════════════════╝\x1b[0m');
                    renderMenu();
                } else if (key.name === 'return' || key.name === 'enter') {
                    process.stdin.removeListener('keypress', onKeypress);
                    console.clear();
                    resolve(selectedIndex);
                } else if (key.ctrl && key.name === 'c') {
                    if (process.stdin.isTTY) {
                        process.stdin.setRawMode(false);
                    }
                    process.exit();
                }
            };

            process.stdin.on('keypress', onKeypress);
        });
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

class ServerScraper {
    constructor(settings) {
        this.settings = settings;
        this.foundInvites = new Set();
        this.inviteDetails = new Map(); // Store full invite details
        this.checkedCodes = new Set();
        this.stats = {
            checked: 0,
            found: 0,
            failed: 0,
            scraped: 0,
            duplicates: 0,
            rateLimited: 0,
            expired: 0,
            filtered: 0
        };
        this.lastSaveCount = 0;
        this.running = true;
        this.consecutiveRateLimits = 0;
        this.rateLimitBackoff = 1000;
        this.dictionaryWords = [];
        this.startTime = Date.now();
        this.requestQueue = [];
        this.activeRequests = 0;
        this.lastProgressUpdate = 0;
        this.proxies = [];
        this.currentProxyIndex = 0;
        this.discordToken = null;
    }

    // Get random user agent
    getRandomUserAgent() {
        return CONFIG.userAgents[Math.floor(Math.random() * CONFIG.userAgents.length)];
    }

    // Get randomized headers
    getRandomHeaders() {
        const acceptLanguages = ['en-US,en;q=0.9', 'en-GB,en;q=0.9', 'en-US,en;q=0.5'];
        const accepts = [
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        ];

        return {
            'User-Agent': this.getRandomUserAgent(),
            'Accept': accepts[Math.floor(Math.random() * accepts.length)],
            'Accept-Language': acceptLanguages[Math.floor(Math.random() * acceptLanguages.length)],
            'Accept-Encoding': 'identity',
            'Connection': 'close',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': Math.random() > 0.5 ? '1' : undefined
        };
    }

    // Load proxies from file
    async loadProxies() {
        if (!this.settings.useProxies) return false;

        try {
            const data = await fs.readFile(CONFIG.proxyFile, 'utf8');
            this.proxies = data.split('\n')
                .map(line => line.trim())
                .filter(line => line && !line.startsWith('#'));

            if (this.proxies.length > 0) {
                console.log(`\x1b[36m🌐 Loaded ${this.proxies.length} proxies\x1b[0m`);
                return true;
            } else {
                console.log('\x1b[33m⚠️  No proxies found in proxies.txt\x1b[0m');
                return false;
            }
        } catch (error) {
            console.log(`\x1b[33m⚠️  Could not load proxies: ${error.message}\x1b[0m`);
            console.log('\x1b[90m  Create proxies.txt with format: http://host:port or http://user:pass@host:port\x1b[0m');
            return false;
        }
    }

    // Load Discord token
    async loadDiscordToken() {
        if (!this.settings.useDiscordToken) return false;

        try {
            const token = await fs.readFile(CONFIG.tokenFile, 'utf8');
            this.discordToken = token.trim();

            if (this.discordToken) {
                console.log(`\x1b[36m🔑 Loaded Discord bot token\x1b[0m`);
                return true;
            }
        } catch (error) {
            console.log(`\x1b[33m⚠️  Could not load token: ${error.message}\x1b[0m`);
            console.log('\x1b[90m  Create discord_token.txt with your bot token for 10x higher rate limits\x1b[0m');
        }
        return false;
    }

    // Get next proxy
    getNextProxy() {
        if (!this.settings.useProxies || this.proxies.length === 0) return null;

        const proxy = this.proxies[this.currentProxyIndex];
        this.currentProxyIndex = (this.currentProxyIndex + 1) % this.proxies.length;
        return proxy;
    }

    // Fetch words from dictionary API
    async fetchDictionaryWords() {
        if (this.dictionaryWords.length > 0) return;

        try {
            console.log('\x1b[36m📚 Fetching words from dictionary API...\x1b[0m');
            const response = await this.makeRequest('https://random-word-api.herokuapp.com/word?number=100');

            if (response.statusCode === 200) {
                const words = JSON.parse(response.body);
                if (Array.isArray(words)) {
                    this.dictionaryWords = words.filter(w => w.length >= 3 && w.length <= 12);
                    console.log(`\x1b[32m  ✓ Loaded ${this.dictionaryWords.length} dictionary words\x1b[0m`);
                }
            }
        } catch (error) {
            this.debug(`Failed to fetch dictionary words: ${error.message}`);
        }
    }

    debug(message) {
        if (this.settings.showDebug) {
            console.log(`\x1b[90m  [DEBUG] ${message}\x1b[0m`);
        }
    }

    // Calculate ETA
    getETA() {
        const elapsed = Date.now() - this.startTime;
        const rate = this.stats.found / (elapsed / 1000);
        if (rate === 0) return 'Calculating...';

        const remaining = this.settings.maxInvites - this.foundInvites.size;
        const secondsLeft = remaining / rate;

        if (secondsLeft > 3600) {
            return `${(secondsLeft / 3600).toFixed(1)}h`;
        } else if (secondsLeft > 60) {
            return `${(secondsLeft / 60).toFixed(1)}m`;
        } else {
            return `${secondsLeft.toFixed(0)}s`;
        }
    }

    // Get progress bar
    getProgressBar(width = 30) {
        const progress = this.foundInvites.size / this.settings.maxInvites;
        const filled = Math.floor(progress * width);
        const empty = width - filled;
        const bar = '█'.repeat(filled) + '░'.repeat(empty);
        return `[${bar}] ${(progress * 100).toFixed(1)}%`;
    }

    // Update progress display
    updateProgress() {
        const now = Date.now();
        if (now - this.lastProgressUpdate < 2000) return;
        this.lastProgressUpdate = now;

        const elapsed = ((now - this.startTime) / 1000 / 60).toFixed(1);
        console.log(`\x1b[90m  Progress: ${this.getProgressBar()} | Found: ${this.foundInvites.size}/${this.settings.maxInvites} | Time: ${elapsed}m | ETA: ${this.getETA()}\x1b[0m`);
    }

    // Save checkpoint
    async saveCheckpoint() {
        try {
            const checkpoint = {
                foundInvites: Array.from(this.foundInvites),
                checkedCodes: Array.from(this.checkedCodes),
                inviteDetails: Array.from(this.inviteDetails.entries()),
                stats: this.stats,
                timestamp: Date.now()
            };
            await fs.writeFile(CONFIG.checkpointFile, JSON.stringify(checkpoint, null, 2));
            this.debug('Checkpoint saved');
        } catch (error) {
            this.debug(`Checkpoint save failed: ${error.message}`);
        }
    }

    // Load checkpoint
    async loadCheckpoint() {
        try {
            const data = await fs.readFile(CONFIG.checkpointFile, 'utf8');
            const checkpoint = JSON.parse(data);

            checkpoint.foundInvites.forEach(invite => this.foundInvites.add(invite));
            checkpoint.checkedCodes.forEach(code => this.checkedCodes.add(code));
            checkpoint.inviteDetails.forEach(([key, value]) => this.inviteDetails.set(key, value));
            Object.assign(this.stats, checkpoint.stats);

            console.log(`\x1b[36m📂 Resumed from checkpoint (${this.foundInvites.size} invites)\x1b[0m`);
            return true;
        } catch (error) {
            this.debug('No checkpoint found or invalid');
            return false;
        }
    }

    // Process invite with queue
    async queueInviteCheck(inviteCode) {
        return new Promise((resolve) => {
            this.requestQueue.push({ inviteCode, resolve });
            this.processQueue();
        });
    }

    // Process the queue with concurrency control
    async processQueue() {
        while (this.requestQueue.length > 0 && this.activeRequests < this.settings.concurrentRequests) {
            const item = this.requestQueue.shift();
            if (!item) continue;

            this.activeRequests++;

            this.checkInvite(item.inviteCode).then((result) => {
                this.activeRequests--;
                item.resolve(result);
                this.processQueue();
            }).catch((error) => {
                this.activeRequests--;
                this.debug(`Queue error: ${error.message}`);
                item.resolve(null);
                this.processQueue();
            });
        }
    }

    async makeRequest(url, options = {}, retryCount = 0) {
        if (!this.running) throw new Error('Scraper stopped');

        return new Promise(async (resolve, reject) => {
            const timeoutId = setTimeout(() => {
                reject(new Error('Request timeout'));
            }, CONFIG.timeout);

            try {
                const urlObj = new URL(url);
                const client = urlObj.protocol === 'https:' ? https : http;

                const requestOptions = {
                    method: options.method || 'GET',
                    headers: {
                        ...this.getRandomHeaders(),
                        ...options.headers
                    }
                };

                // Add Discord bot token for authenticated requests
                if (this.discordToken && url.includes('discord.com/api')) {
                    requestOptions.headers['Authorization'] = `Bot ${this.discordToken}`;
                }

                // Add proxy support
                const proxy = this.getNextProxy();
                if (proxy && HttpsProxyAgent) {
                    try {
                        requestOptions.agent = new HttpsProxyAgent(proxy);
                        this.debug(`Using proxy: ${proxy.split('@').pop()}`);
                    } catch (proxyError) {
                        this.debug(`Proxy error: ${proxyError.message}`);
                    }
                }

                const req = client.request(url, requestOptions, (res) => {
                    if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                        clearTimeout(timeoutId);
                        const redirectUrl = res.headers.location.startsWith('http')
                            ? res.headers.location
                            : new URL(res.headers.location, url).href;
                        this.makeRequest(redirectUrl, options, retryCount).then(resolve).catch(reject);
                        return;
                    }

                    let data = '';
                    res.on('data', (chunk) => data += chunk);
                    res.on('end', () => {
                        clearTimeout(timeoutId);
                        resolve({ statusCode: res.statusCode, headers: res.headers, body: data });
                    });
                    res.on('error', (error) => {
                        clearTimeout(timeoutId);
                        reject(error);
                    });
                });

                req.on('error', (error) => {
                    clearTimeout(timeoutId);
                    reject(error);
                });

                req.setTimeout(CONFIG.timeout);
                if (options.body) req.write(options.body);
                req.end();
            } catch (error) {
                clearTimeout(timeoutId);
                if (retryCount < CONFIG.retryAttempts) {
                    this.debug(`Retry ${retryCount + 1}/${CONFIG.retryAttempts} for ${url}`);
                    await this.delay(CONFIG.retryDelay);
                    this.makeRequest(url, options, retryCount + 1).then(resolve).catch(reject);
                } else {
                    reject(error);
                }
            }
        });
    }

    // Check invite using Widget API (alternative method with different rate limits)
    async checkInviteWidget(inviteCode) {
        try {
            const cleanCode = inviteCode.replace(/^(https?:\/\/)?(discord\.gg\/|discord\.com\/invite\/)/, '').trim();

            // First, try to get guild ID from invite
            const inviteUrl = `https://discord.com/api/v10/invites/${cleanCode}?with_counts=false`;
            const inviteRes = await this.makeRequest(inviteUrl);

            if (inviteRes.statusCode !== 200) return null;

            const inviteData = JSON.parse(inviteRes.body);
            if (!inviteData.guild || !inviteData.guild.id) return null;

            // Now use widget API to get more info
            const widgetUrl = `https://discord.com/api/guilds/${inviteData.guild.id}/widget.json`;
            const widgetRes = await this.makeRequest(widgetUrl);

            if (widgetRes.statusCode === 200) {
                const widgetData = JSON.parse(widgetRes.body);
                // Combine data from both APIs
                return {
                    ...inviteData,
                    approximate_member_count: widgetData.presence_count || 0,
                    widgetEnabled: true
                };
            }

            // Widget not enabled, return basic invite data
            return inviteData;
        } catch (error) {
            this.debug(`Widget check error: ${error.message}`);
            return null;
        }
    }

    async checkInvite(inviteCode) {
        if (!this.running || this.foundInvites.size >= this.settings.maxInvites) {
            return null;
        }

        try {
            const cleanCode = inviteCode.replace(/^(https?:\/\/)?(discord\.gg\/|discord\.com\/invite\/)/, '').trim();

            if (this.checkedCodes.has(cleanCode)) {
                this.stats.duplicates++;
                return null;
            }

            this.checkedCodes.add(cleanCode);

            if (!cleanCode || cleanCode.length < 2 || cleanCode.length > 32 || cleanCode.includes(' ') || cleanCode.includes('/')) {
                return null;
            }

            // Use Widget API if enabled
            if (this.settings.useWidgetAPI) {
                const widgetData = await this.checkInviteWidget(cleanCode);
                if (widgetData) {
                    this.stats.checked++;
                    const memberCount = widgetData.approximate_member_count || 0;

                    if (memberCount < this.settings.minMemberCount) {
                        this.stats.filtered++;
                        this.debug(`Filtered ${cleanCode} (${memberCount} < ${this.settings.minMemberCount} members)`);
                        return null;
                    }

                    this.stats.found++;
                    this.consecutiveRateLimits = 0;

                    this.inviteDetails.set(cleanCode, {
                        code: cleanCode,
                        guildName: widgetData.guild.name,
                        guildId: widgetData.guild.id,
                        memberCount: memberCount,
                        features: widgetData.guild.features || [],
                        description: widgetData.guild.description || null,
                        banner: widgetData.guild.banner || null,
                        icon: widgetData.guild.icon || null
                    });

                    console.log(`\x1b[32m  ✓ ${cleanCode}\x1b[0m - \x1b[37m${widgetData.guild.name.substring(0, 40)}\x1b[0m \x1b[90m(${memberCount} members)\x1b[0m`);

                    if (this.stats.found - this.lastSaveCount >= this.settings.autoSaveInterval) {
                        await this.saveInvites();
                        await this.saveCheckpoint();
                        this.lastSaveCount = this.stats.found;
                    }

                    this.updateProgress();
                    return cleanCode;
                }
                // Fall back to regular API if widget fails
            }

            const url = `https://discord.com/api/v10/invites/${cleanCode}?with_counts=true`;
            const response = await this.makeRequest(url);
            this.stats.checked++;

            if (response.statusCode === 200) {
                try {
                    const data = JSON.parse(response.body);
                    if (data.guild && data.code) {
                        const memberCount = data.approximate_member_count || 0;

                        // Filter by minimum member count
                        if (memberCount < this.settings.minMemberCount) {
                            this.stats.filtered++;
                            this.debug(`Filtered ${cleanCode} (${memberCount} < ${this.settings.minMemberCount} members)`);
                            return null;
                        }

                        this.stats.found++;
                        this.consecutiveRateLimits = 0; // Reset on success
                        const guildName = data.guild.name.substring(0, 40);

                        // Store full invite details
                        this.inviteDetails.set(cleanCode, {
                            code: cleanCode,
                            guildName: data.guild.name,
                            guildId: data.guild.id,
                            memberCount: memberCount,
                            features: data.guild.features || [],
                            description: data.guild.description || null,
                            banner: data.guild.banner || null,
                            icon: data.guild.icon || null
                        });

                        console.log(`\x1b[32m  ✓ ${cleanCode}\x1b[0m - \x1b[37m${guildName}\x1b[0m \x1b[90m(${memberCount} members)\x1b[0m`);

                        if (this.stats.found - this.lastSaveCount >= this.settings.autoSaveInterval) {
                            await this.saveInvites();
                            await this.saveCheckpoint();
                            this.lastSaveCount = this.stats.found;
                        }

                        this.updateProgress();
                        return cleanCode;
                    }
                } catch (parseError) {
                    this.debug(`Parse error for ${cleanCode}: ${parseError.message}`);
                }
            } else if (response.statusCode === 404) {
                this.stats.expired++;
                this.debug(`Expired/Invalid: ${cleanCode}`);
            } else if (response.statusCode === 429) {
                this.stats.rateLimited++;
                this.consecutiveRateLimits++;

                // Exponential backoff for rate limits
                const waitTime = Math.min(this.rateLimitBackoff * this.consecutiveRateLimits, 30000);
                console.log(`\x1b[33m  ⚠️ Rate limited! Waiting ${waitTime/1000}s... (${this.consecutiveRateLimits} consecutive)\x1b[0m`);
                await this.delay(waitTime);

                // If too many consecutive rate limits, stop this source
                if (this.consecutiveRateLimits >= 10) {
                    console.log(`\x1b[31m  ❌ Too many rate limits, stopping this source\x1b[0m`);
                    throw new Error('Rate limit exceeded');
                }
            } else {
                this.debug(`Status ${response.statusCode} for ${cleanCode}`);
            }

            this.stats.failed++;
            return null;
        } catch (error) {
            this.stats.failed++;
            this.debug(`Error checking ${inviteCode}: ${error.message}`);
            return null;
        }
    }

    extractInvitesFromText(text) {
        const invites = new Set();
        const patterns = [
            /discord\.gg\/([a-zA-Z0-9-_]{2,32})/gi,
            /discord\.com\/invite\/([a-zA-Z0-9-_]{2,32})/gi,
            /discordapp\.com\/invite\/([a-zA-Z0-9-_]{2,32})/gi,
            /\/invite\/([a-zA-Z0-9-_]{2,32})/gi,
            /"code":\s*"([a-zA-Z0-9-_]{2,32})"/gi,
            /"invite":\s*"([a-zA-Z0-9-_]{2,32})"/gi,
            /href="https:\/\/discord\.gg\/([a-zA-Z0-9-_]{2,32})"/gi,
            /data-code="([a-zA-Z0-9-_]{2,32})"/gi,
        ];

        for (const pattern of patterns) {
            const matches = text.matchAll(pattern);
            for (const match of matches) {
                if (match[1] && match[1].length >= 2 && match[1].length <= 32) {
                    invites.add(match[1]);
                }
            }
        }

        return Array.from(invites);
    }

    // Helper to process invite codes (either verify or collect raw)
    async processInviteCode(inviteCode) {
        if (this.settings.skipVerification) {
            // Raw mode: just collect codes
            const cleanCode = inviteCode.replace(/^(https?:\/\/)?(discord\.gg\/|discord\.com\/invite\/)/, '').trim();
            if (!this.checkedCodes.has(cleanCode) && cleanCode.length >= 2 && cleanCode.length <= 32 && !cleanCode.includes(' ') && !cleanCode.includes('/')) {
                this.foundInvites.add(cleanCode);
                this.checkedCodes.add(cleanCode);
                this.stats.scraped++;
                console.log(`\x1b[36m  + ${cleanCode}\x1b[0m`);
                return cleanCode;
            }
            return null;
        } else {
            // Normal mode: verify each invite
            const invite = await this.checkInvite(inviteCode);
            if (invite) {
                this.foundInvites.add(invite);
                this.stats.scraped++;
                return invite;
            }
            await this.delay(this.settings.requestDelay);
            return null;
        }
    }

    async withTimeout(asyncFunc, timeoutMs, name) {
        return Promise.race([
            asyncFunc(),
            new Promise((_, reject) =>
                setTimeout(() => reject(new Error(`Timeout: ${name}`)), timeoutMs)
            )
        ]);
    }

    async scrapeMGCounts() {
        console.log('\n\x1b[36m📋 [1/8] tags.mgcounts.com\x1b[0m');
        const startCount = this.foundInvites.size;
        this.consecutiveRateLimits = 0; // Reset for new source

        try {
            await this.withTimeout(async () => {
                const response = await this.makeRequest('https://tags.mgcounts.com');
                if (response.statusCode === 200) {
                    const invites = this.extractInvitesFromText(response.body);
                    console.log(`\x1b[90m  Extracted ${invites.length} potential invites\x1b[0m`);

                    for (const inviteCode of invites) {
                        if (this.foundInvites.size >= this.settings.maxInvites) break;
                        if (!this.settings.skipVerification && this.consecutiveRateLimits >= 10) break;
                        await this.processInviteCode(inviteCode);
                    }
                }
            }, CONFIG.sourceTimeout * 2, 'MGCounts');
            console.log(`\x1b[32m  ✓ Found ${this.foundInvites.size - startCount} new invites\x1b[0m`);
        } catch (error) {
            console.log(`\x1b[33m  ⚠ Skipped: ${error.message}\x1b[0m`);
        }

        // Cool down between sources
        await this.delay(2000);
    }

    async scrapeDiscordGuildTags() {
        console.log('\n\x1b[36m📋 [2/8] discordguildtags.com\x1b[0m');
        const startCount = this.foundInvites.size;
        this.consecutiveRateLimits = 0;

        const urls = ['https://discordguildtags.com/', 'https://discordguildtags.com/tags'];

        for (const url of urls) {
            if (this.foundInvites.size >= this.settings.maxInvites) break;
            if (!this.settings.skipVerification && this.consecutiveRateLimits >= 10) break;

            try {
                await this.withTimeout(async () => {
                    const response = await this.makeRequest(url);
                    if (response.statusCode === 200) {
                        const invites = this.extractInvitesFromText(response.body);
                        console.log(`\x1b[90m  Extracted ${invites.length} invites\x1b[0m`);

                        for (const inviteCode of invites) {
                            if (this.foundInvites.size >= this.settings.maxInvites) break;
                            if (!this.settings.skipVerification && this.consecutiveRateLimits >= 10) break;
                            await this.processInviteCode(inviteCode);
                        }
                    }
                }, CONFIG.sourceTimeout / 2, url);
            } catch (error) {
                console.log(`\x1b[33m  ⚠ Skipped\x1b[0m`);
            }
        }
        console.log(`\x1b[32m  ✓ Found ${this.foundInvites.size - startCount} new invites\x1b[0m`);
        await this.delay(2000);
    }

    async scrapeDisboard() {
        console.log('\n\x1b[36m📋 [3/8] disboard.org\x1b[0m');
        const startCount = this.foundInvites.size;
        this.consecutiveRateLimits = 0;

        const tags = ['tag', 'gaming', 'community', 'anime', 'social', 'memes', 'fun', 'music'];

        for (const tag of tags) {
            if (this.foundInvites.size >= this.settings.maxInvites) break;
            if (this.consecutiveRateLimits >= 10) break;

            console.log(`\x1b[90m  Tag: ${tag}\x1b[0m`);

            for (let page = 1; page <= 3; page++) {
                if (this.foundInvites.size >= this.settings.maxInvites) break;
                if (this.consecutiveRateLimits >= 10) break;

                try {
                    await this.withTimeout(async () => {
                        const url = `https://disboard.org/servers/tag/${tag}${page > 1 ? `/${page}` : ''}`;
                        const response = await this.makeRequest(url);

                        if (response.statusCode === 200) {
                            const invites = this.extractInvitesFromText(response.body);
                            this.debug(`Page ${page}: ${invites.length} invites`);

                            for (const inviteCode of invites) {
                                if (this.foundInvites.size >= this.settings.maxInvites) break;
                                if (!this.settings.skipVerification && this.consecutiveRateLimits >= 10) break;
                                await this.processInviteCode(inviteCode);
                            }
                        }
                        await this.delay(this.settings.requestDelay * 2);
                    }, 30000, `Disboard ${tag} p${page}`);
                } catch (error) {
                    this.debug(`Failed ${tag} page ${page}`);
                    break;
                }
            }
        }
        console.log(`\x1b[32m  ✓ Found ${this.foundInvites.size - startCount} new invites\x1b[0m`);
        await this.delay(2000);
    }

    async scrapeTopGG() {
        console.log('\n\x1b[36m📋 [4/8] top.gg\x1b[0m');
        const startCount = this.foundInvites.size;
        this.consecutiveRateLimits = 0;

        const urls = [
            'https://top.gg/servers',
            'https://top.gg/servers/tag/community',
            'https://top.gg/servers/tag/gaming',
            'https://top.gg/servers/tag/social'
        ];

        for (const url of urls) {
            if (this.foundInvites.size >= this.settings.maxInvites) break;
            if (this.consecutiveRateLimits >= 10) break;

            try {
                await this.withTimeout(async () => {
                    const response = await this.makeRequest(url);
                    if (response.statusCode === 200) {
                        const invites = this.extractInvitesFromText(response.body);
                        console.log(`\x1b[90m  Extracted ${invites.length} invites\x1b[0m`);

                        for (const inviteCode of invites) {
                            if (this.foundInvites.size >= this.settings.maxInvites) break;
                            if (!this.settings.skipVerification && this.consecutiveRateLimits >= 10) break;
                            await this.processInviteCode(inviteCode);
                        }
                    }
                }, CONFIG.sourceTimeout / 2, url);
            } catch (error) {
                this.debug(`Failed ${url}`);
            }
        }
        console.log(`\x1b[32m  ✓ Found ${this.foundInvites.size - startCount} new invites\x1b[0m`);
        await this.delay(2000);
    }

    async scrapeDiscordMe() {
        console.log('\n\x1b[36m📋 [5/8] discord.me\x1b[0m');
        const startCount = this.foundInvites.size;
        this.consecutiveRateLimits = 0;

        const categories = ['gaming', 'anime', 'music', 'community', 'technology'];

        for (const category of categories) {
            if (this.foundInvites.size >= this.settings.maxInvites) break;
            if (this.consecutiveRateLimits >= 10) break;

            console.log(`\x1b[90m  Category: ${category}\x1b[0m`);

            try {
                await this.withTimeout(async () => {
                    const url = `https://discord.me/servers/${category}`;
                    const response = await this.makeRequest(url);

                    if (response.statusCode === 200) {
                        const invites = this.extractInvitesFromText(response.body);
                        this.debug(`${category}: ${invites.length} invites`);

                        for (const inviteCode of invites) {
                            if (this.foundInvites.size >= this.settings.maxInvites) break;
                            if (!this.settings.skipVerification && this.consecutiveRateLimits >= 10) break;
                            await this.processInviteCode(inviteCode);
                        }
                    }
                }, 30000, `Discord.me ${category}`);
            } catch (error) {
                this.debug(`Failed ${category}`);
            }
        }
        console.log(`\x1b[32m  ✓ Found ${this.foundInvites.size - startCount} new invites\x1b[0m`);
        await this.delay(2000);
    }

    async scrapeDiscordSt() {
        console.log('\n\x1b[36m📋 [6/8] discord.st\x1b[0m');
        const startCount = this.foundInvites.size;
        this.consecutiveRateLimits = 0;

        try {
            await this.withTimeout(async () => {
                const url = 'https://discord.st/servers';
                const response = await this.makeRequest(url);

                if (response.statusCode === 200) {
                    const invites = this.extractInvitesFromText(response.body);
                    console.log(`\x1b[90m  Extracted ${invites.length} invites\x1b[0m`);

                    for (const inviteCode of invites) {
                        if (this.foundInvites.size >= this.settings.maxInvites) break;
                        if (!this.settings.skipVerification && this.consecutiveRateLimits >= 10) break;
                        await this.processInviteCode(inviteCode);
                    }
                }
            }, 30000, 'Discord.st');
        } catch (error) {
            this.debug(`Failed discord.st`);
        }

        console.log(`\x1b[32m  ✓ Found ${this.foundInvites.size - startCount} new invites\x1b[0m`);
        await this.delay(2000);
    }

    async scrapeDiscordServers() {
        console.log('\n\x1b[36m📋 [7/8] discordservers.com\x1b[0m');
        const startCount = this.foundInvites.size;
        this.consecutiveRateLimits = 0;

        const categories = ['gaming', 'anime', 'music', 'community'];

        for (const category of categories) {
            if (this.foundInvites.size >= this.settings.maxInvites) break;
            if (this.consecutiveRateLimits >= 10) break;

            try {
                await this.withTimeout(async () => {
                    const url = `https://discordservers.com/browse/${category}`;
                    const response = await this.makeRequest(url);

                    if (response.statusCode === 200) {
                        const invites = this.extractInvitesFromText(response.body);
                        this.debug(`${category}: ${invites.length} invites`);

                        for (const inviteCode of invites) {
                            if (this.foundInvites.size >= this.settings.maxInvites) break;
                            if (!this.settings.skipVerification && this.consecutiveRateLimits >= 10) break;
                            await this.processInviteCode(inviteCode);
                        }
                    }
                }, 30000, `DiscordServers ${category}`);
            } catch (error) {
                this.debug(`Failed ${category}`);
            }
        }

        console.log(`\x1b[32m  ✓ Found ${this.foundInvites.size - startCount} new invites\x1b[0m`);
        await this.delay(2000);
    }

    async scrapeGoogleSearch() {
        console.log('\n\x1b[36m📋 [8/8] Google Search\x1b[0m');
        console.log('\x1b[33m  ⚠️  Google aggressively blocks automated requests - SKIPPED\x1b[0m');
        console.log('\x1b[90m  Tip: Use proxies or VPS for better results\x1b[0m');

        // Google scraping disabled - too aggressive rate limiting
        // Use Bing or DuckDuckGo as alternatives, or enable proxies

        return;
    }

    generateRandomInvite() {
        const length = CONFIG.inviteLength[Math.floor(Math.random() * CONFIG.inviteLength.length)];
        let code = '';
        for (let i = 0; i < length; i++) {
            code += CONFIG.charactersPool.charAt(Math.floor(Math.random() * CONFIG.charactersPool.length));
        }
        return code;
    }

    generateVanityInvite() {
        // Use dictionary words if available, otherwise use common words
        const wordList = this.dictionaryWords.length > 0
            ? [...this.dictionaryWords, ...CONFIG.commonWords]
            : CONFIG.commonWords;

        const word = wordList[Math.floor(Math.random() * wordList.length)];
        const variations = [
            word,
            word + Math.floor(Math.random() * 100),
            word + Math.floor(Math.random() * 1000),
            word + 'hq',
            word + 'official',
            'the' + word,
            word + 'server',
            word + 'community',
            word + 'hub',
            word + 'discord',
            word + Math.floor(Math.random() * 10000)
        ];
        return variations[Math.floor(Math.random() * variations.length)];
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async saveInvites() {
        try {
            const invitesArray = Array.from(this.foundInvites);

            const dir = path.dirname(CONFIG.outputFile);
            try {
                await fs.access(dir);
            } catch {
                await fs.mkdir(dir, { recursive: true });
            }

            // Always save simple invite codes
            await fs.writeFile(CONFIG.outputFile, JSON.stringify(invitesArray, null, 2), 'utf8');

            const timestamp = new Date().toLocaleTimeString();

            // Only save detailed info if NOT in raw mode
            if (!this.settings.skipVerification) {
                const detailsArray = Array.from(this.inviteDetails.values());

                // Save detailed info
                const detailsFile = CONFIG.outputFile.replace('.json', '_detailed.json');
                await fs.writeFile(detailsFile, JSON.stringify(detailsArray, null, 2), 'utf8');

                // Save as CSV
                const csvFile = CONFIG.outputFile.replace('.json', '.csv');
                const csvData = this.generateCSV(detailsArray);
                await fs.writeFile(csvFile, csvData, 'utf8');

                console.log(`\x1b[35m💾 [${timestamp}] Saved ${invitesArray.length} invites (JSON, CSV, Details)\x1b[0m`);
            } else {
                // Raw mode - only JSON
                console.log(`\x1b[35m💾 [${timestamp}] Saved ${invitesArray.length} invite codes (unverified)\x1b[0m`);
            }
        } catch (error) {
            console.error(`\x1b[31m❌ Save failed: ${error.message}\x1b[0m`);
        }
    }

    generateCSV(details) {
        const headers = ['Code', 'Guild Name', 'Guild ID', 'Members', 'Features', 'Description', 'Invite URL'];
        const rows = details.map(d => [
            d.code,
            `"${(d.guildName || '').replace(/"/g, '""')}"`,
            d.guildId,
            d.memberCount,
            `"${(d.features || []).join(', ')}"`,
            `"${(d.description || '').replace(/"/g, '""')}"`,
            `https://discord.gg/${d.code}`
        ].join(','));
        return [headers.join(','), ...rows].join('\n');
    }

    async loadExistingInvites() {
        try {
            const data = await fs.readFile(CONFIG.outputFile, 'utf8');
            const invites = JSON.parse(data);
            if (Array.isArray(invites)) {
                invites.forEach(invite => {
                    const cleanCode = invite.replace(/^(https?:\/\/)?(discord\.gg\/|discord\.com\/invite\/)/, '');
                    this.foundInvites.add(cleanCode);
                    this.checkedCodes.add(cleanCode);
                });
                console.log(`\x1b[36m📂 Loaded ${invites.length} existing invites\x1b[0m`);
            }
        } catch (error) {
            console.log('\x1b[36m📂 Starting fresh\x1b[0m');
        }
    }

    printStats() {
        const elapsed = ((Date.now() - this.startTime) / 1000 / 60).toFixed(2);

        // In raw mode, use total collected; in normal mode, use found (verified)
        const totalCollected = this.settings.skipVerification ? this.foundInvites.size : this.stats.found;
        const rate = totalCollected / (elapsed || 1);

        const successRate = this.stats.checked > 0
            ? ((this.stats.found / this.stats.checked) * 100).toFixed(2)
            : (this.settings.skipVerification ? 'N/A (raw mode)' : '0.00');

        console.log('\n\x1b[36m╔═══════════════════════════════════════════════════════╗\x1b[0m');
        console.log('\x1b[36m║                      Statistics                       ║\x1b[0m');
        console.log('\x1b[36m╠═══════════════════════════════════════════════════════╣\x1b[0m');

        if (!this.settings.skipVerification) {
            console.log(`\x1b[36m║\x1b[0m  Checked:     \x1b[33m${this.stats.checked.toString().padEnd(39)}\x1b[36m║\x1b[0m`);
            console.log(`\x1b[36m║\x1b[0m  Valid:       \x1b[32m${this.stats.found.toString().padEnd(39)}\x1b[36m║\x1b[0m`);
            console.log(`\x1b[36m║\x1b[0m  Failed:      \x1b[31m${this.stats.failed.toString().padEnd(39)}\x1b[36m║\x1b[0m`);
            console.log(`\x1b[36m║\x1b[0m  Expired:     \x1b[33m${this.stats.expired.toString().padEnd(39)}\x1b[36m║\x1b[0m`);
            console.log(`\x1b[36m║\x1b[0m  Filtered:    \x1b[35m${this.stats.filtered.toString().padEnd(39)}\x1b[36m║\x1b[0m`);
            console.log(`\x1b[36m║\x1b[0m  Rate Limited:\x1b[31m${this.stats.rateLimited.toString().padEnd(39)}\x1b[36m║\x1b[0m`);
        }

        console.log(`\x1b[36m║\x1b[0m  From Scrape: \x1b[35m${this.stats.scraped.toString().padEnd(39)}\x1b[36m║\x1b[0m`);
        console.log(`\x1b[36m║\x1b[0m  Duplicates:  \x1b[90m${this.stats.duplicates.toString().padEnd(39)}\x1b[36m║\x1b[0m`);

        if (!this.settings.skipVerification) {
            console.log(`\x1b[36m║\x1b[0m  Success Rate:\x1b[32m${(successRate + '%').padEnd(39)}\x1b[36m║\x1b[0m`);
        }

        console.log(`\x1b[36m║\x1b[0m  Total Unique:\x1b[1m\x1b[32m${this.foundInvites.size.toString().padEnd(39)}\x1b[0m\x1b[36m║\x1b[0m`);
        console.log(`\x1b[36m║\x1b[0m  Time Elapsed:\x1b[90m${(elapsed + ' min').padEnd(39)}\x1b[36m║\x1b[0m`);
        console.log(`\x1b[36m║\x1b[0m  Collection Rate:\x1b[90m${(rate.toFixed(2) + ' codes/min').padEnd(36)}\x1b[36m║\x1b[0m`);
        console.log('\x1b[36m╚═══════════════════════════════════════════════════════╝\x1b[0m\n');
    }

    async run() {
        console.clear();
        console.log('\x1b[36m╔═══════════════════════════════════════════════════════╗\x1b[0m');
        console.log('\x1b[36m║         Discord Server Scraper v4.0 - Running         ║\x1b[0m');
        console.log('\x1b[36m╚═══════════════════════════════════════════════════════╝\x1b[0m\n');
        console.log(`\x1b[33m🎯 Target:\x1b[0m ${this.settings.maxInvites} invites`);
        console.log(`\x1b[33m📁 Output:\x1b[0m ${CONFIG.outputFile}`);
        console.log(`\x1b[33m💾 Auto-save:\x1b[0m Every ${this.settings.autoSaveInterval} invites`);
        console.log(`\x1b[33m⚡ Workers:\x1b[0m ${this.settings.concurrentRequests} concurrent`);
        console.log(`\x1b[33m👥 Min Members:\x1b[0m ${this.settings.minMemberCount}`);
        console.log(`\x1b[33m✅ Verification:\x1b[0m ${this.settings.skipVerification ? 'SKIPPED (Raw mode)' : 'Enabled'}`);
        console.log(`\x1b[33m🐛 Debug:\x1b[0m ${this.settings.showDebug ? 'Enabled' : 'Disabled'}\n`);

        if (this.settings.skipVerification) {
            console.log('\x1b[36m⚡ RAW MODE: Collecting invite codes without verification\x1b[0m');
            console.log('\x1b[90m  Codes will be verified later by /find_tags command\x1b[0m');
            console.log('\x1b[90m  Much faster! No rate limiting!\x1b[0m\n');
        }

        // Load proxies and token if enabled
        await this.loadProxies();
        await this.loadDiscordToken();

        // Try to resume from checkpoint
        if (this.settings.resumeFromCheckpoint) {
            const resumed = await this.loadCheckpoint();
            if (resumed) {
                console.log(`\x1b[32m  ✓ Resumed with ${this.foundInvites.size} existing invites\x1b[0m\n`);
                this.startTime = Date.now(); // Reset timer for current session
            }
        }

        await this.loadExistingInvites();

        if (this.settings.enableWebScraping) {
            console.log('\x1b[1m\x1b[36m🌐 Web Scraping Phase\x1b[0m');

            // Fetch dictionary words for better vanity testing
            await this.fetchDictionaryWords();

            await this.scrapeMGCounts();
            if (this.foundInvites.size >= this.settings.maxInvites) {
                this.running = false;
                await this.saveInvites();
                this.printStats();
                return;
            }

            await this.scrapeDiscordGuildTags();
            if (this.foundInvites.size >= this.settings.maxInvites) {
                this.running = false;
                await this.saveInvites();
                this.printStats();
                return;
            }

            await this.scrapeDisboard();
            if (this.foundInvites.size >= this.settings.maxInvites) {
                this.running = false;
                await this.saveInvites();
                this.printStats();
                return;
            }

            await this.scrapeTopGG();
            if (this.foundInvites.size >= this.settings.maxInvites) {
                this.running = false;
                await this.saveInvites();
                this.printStats();
                return;
            }

            await this.scrapeDiscordMe();
            if (this.foundInvites.size >= this.settings.maxInvites) {
                this.running = false;
                await this.saveInvites();
                this.printStats();
                return;
            }

            await this.scrapeDiscordSt();
            if (this.foundInvites.size >= this.settings.maxInvites) {
                this.running = false;
                await this.saveInvites();
                this.printStats();
                return;
            }

            await this.scrapeDiscordServers();
            if (this.foundInvites.size >= this.settings.maxInvites) {
                this.running = false;
                await this.saveInvites();
                this.printStats();
                return;
            }

            await this.scrapeGoogleSearch();
            await this.saveInvites();
        }

        if (this.foundInvites.size >= this.settings.maxInvites) {
            this.running = false;
            this.printStats();
            return;
        }

        if (this.settings.enableVanityTesting && this.foundInvites.size < this.settings.maxInvites) {
            console.log('\n\x1b[1m\x1b[36m🎯 Vanity URL Testing\x1b[0m');
            if (this.settings.skipVerification) {
                console.log('\x1b[90m  Skipped in raw mode - vanity testing requires verification\x1b[0m');
            } else {
                for (let i = 0; i < 200 && this.foundInvites.size < this.settings.maxInvites; i++) {
                    const vanityCode = this.generateVanityInvite();
                    const invite = await this.checkInvite(vanityCode);
                    if (invite) this.foundInvites.add(invite);
                    await this.delay(this.settings.requestDelay);

                    if ((i + 1) % 50 === 0) {
                        console.log(`\x1b[90m  Tested ${i + 1}/200 vanity URLs...\x1b[0m`);
                    }
                }
                await this.saveInvites();
            }
        }

        if (this.foundInvites.size >= this.settings.maxInvites) {
            this.running = false;
            this.printStats();
            return;
        }

        if (this.settings.enableRandomTesting && this.foundInvites.size < this.settings.maxInvites) {
            console.log('\n\x1b[1m\x1b[36m🎲 Random Code Testing\x1b[0m');
            if (this.settings.skipVerification) {
                console.log('\x1b[90m  Skipped in raw mode - random testing requires verification\x1b[0m');
            } else {
                let consecutiveFails = 0;
                const maxFails = 300;

                while (this.foundInvites.size < this.settings.maxInvites && consecutiveFails < maxFails) {
                    const randomCode = this.generateRandomInvite();
                    const invite = await this.checkInvite(randomCode);
                    if (invite) {
                        this.foundInvites.add(invite);
                        consecutiveFails = 0;
                    } else {
                        consecutiveFails++;
                    }
                    await this.delay(this.settings.requestDelay);
                }
                await this.saveInvites();
            }
        }

        this.running = false;
        await this.saveInvites();
        await this.saveCheckpoint();
        this.printStats();

        // Clean up checkpoint on successful completion
        try {
            await fs.unlink(CONFIG.checkpointFile);
            this.debug('Checkpoint cleaned up');
        } catch (error) {
            // Ignore if checkpoint doesn't exist
        }

        console.log('\x1b[32m✨ Scraping completed!\x1b[0m\n');
        console.log(`\x1b[36m📊 Files saved:\x1b[0m`);
        console.log(`  - ${CONFIG.outputFile}`);
        if (!this.settings.skipVerification) {
            console.log(`  - ${CONFIG.outputFile.replace('.json', '_detailed.json')}`);
            console.log(`  - ${CONFIG.outputFile.replace('.json', '.csv')}`);
        }

        if (this.settings.skipVerification) {
            console.log(`\n\x1b[36m💡 Next step:\x1b[0m Use /find_tags command to verify and filter these invites!`);
            console.log(`\x1b[90m   The command will check which servers have guild tags\x1b[0m`);
        }
        console.log();
    }
}

// Main
(async () => {
    try {
        const menu = new InteractiveMenu();
        const settings = await menu.show();

        console.log('\x1b[90mStarting scraper...\x1b[0m\n');

        const scraper = new ServerScraper(settings);
        await scraper.run();

        console.log('\x1b[32m✅ Program completed successfully\x1b[0m');
        process.exit(0);
    } catch (error) {
        console.error('\x1b[31m❌ Fatal error:\x1b[0m', error.message);
        if (error.stack) {
            console.error('\x1b[90m' + error.stack + '\x1b[0m');
        }
        process.exit(1);
    }
})();

module.exports = ServerScraper;
