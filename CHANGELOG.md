# Changelog - Discord Server Scraper

All notable changes to this project will be documented in this file.

## [3.6] - 2026-01-06

### Added
- **Random Word API Integration** - Fetches real words from free dictionary API for better vanity URL testing
- **Google Search Scraping** - Searches Google for Discord servers (no API key needed)
- **Additional Sources**:
  - Discord.st server listings
  - DiscordServers.com
  - ServerHound.com
- **Smart Rate Limit Handling**:
  - Exponential backoff (1s, 2s, 3s, up to 30s)
  - Auto-stop after 10 consecutive rate limits
  - Counter reset on success
  - 2-second cooldown between sources
- **Randomized Request Headers** - Rotates User-Agent, Accept headers, and other fingerprints to avoid detection
- **Enhanced Statistics** - Now tracks expired invites, rate limits, and success rate percentage

### Changed
- Default request delay increased from 400ms to 1200ms (safer)
- Request delay options now: 600ms (Fast), 800ms (Normal), 1200ms (Safe), 2000ms (Very Safe)
- MGCounts timeout doubled to 120 seconds
- Improved regex patterns for better invite extraction

### Fixed
- Fixed progress continuing after target reached
- Fixed auto-save triggering correctly every N invites
- Fixed stdin handling in interactive menu

## [3.5] - 2026-01-06

### Added
- **Discord.me** as 5th scraping source
- **Debug mode** - Optional detailed logging of failures, errors, and rate limits
- Better extraction with 8 regex patterns
- Vanity URL testing increased to 200 attempts

### Changed
- Increased vanity variations from 6 to 9
- Random testing fail limit increased to 300

## [3.0] - 2026-01-06

### Added
- **Interactive Configuration Menu** with arrow key navigation
- Customizable settings:
  - Max invites (50-10000)
  - Request delay
  - Enable/disable scraping phases
  - Auto-save interval
- Beautiful colored console output
- Auto-save every N invites
- Progress stops when target reached

### Changed
- Complete code rewrite for better organization
- Split into InteractiveMenu and ServerScraper classes

## [2.1] - 2026-01-06

### Added
- Multi-layer timeout protection
- Auto-save every 10 invites with timestamps
- Skip mechanism for hanging sources
- Visual progress tracking

### Fixed
- Hanging issues with strict timeout handling
- Connection timeout problems

## [2.0] - 2026-01-06

### Added
- 4 scraping sources:
  - tags.mgcounts.com
  - discordguildtags.com
  - disboard.org (multiple tags and pages)
  - top.gg
- Vanity URL testing
- Random invite code testing
- Duplicate prevention
- Statistics tracking

## [1.0] - 2026-01-06

### Added
- Initial release
- Basic Discord invite validation
- Single source scraping
- JSON file output
