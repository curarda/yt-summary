# YouTube Summary

A Chrome extension and a macOS helper that turn a YouTube video into a summary in a Google Doc. Right-click a YouTube link, a page or a video and choose **YouTube Özetle** (Claude summary) or **Full Transkript** (raw transcript). The result is saved to a new Google Doc and opened for you.

## Who it is for

- Anyone who saves long videos to read or study later.
- Users who want the video's content as a document they can search, annotate and share.

## Why I built it

Long videos are hard to revisit. I wanted a one-click way to get a readable summary of a video, saved in my own Google Drive, without a subscription to a summary service.

## How it works

1. The Chrome extension sends the video URL to a native messaging host on your Mac.
2. The host runs `yt_summarize.py`, which fetches the video's transcript.
3. Claude writes the summary (or the raw transcript is kept as is).
4. The text is uploaded to Google Drive as a native Google Doc.

## Privacy and keys

No API keys are stored in this repository.

- The Anthropic API key is stored by you in the **macOS Keychain** (service name `yt-summary-anthropic`).
- Google OAuth credentials are stored by you in `~/.config/yt-summary/`.

You need your own Anthropic API key and your own Google Cloud OAuth client. Step-by-step instructions are in [SETUP.md](SETUP.md).

## Requirements

- macOS, Python 3, Google Chrome
- An Anthropic API key and a Google Cloud project with the Drive API enabled

## Setup

Follow [SETUP.md](SETUP.md). It covers the Keychain entry, the Google OAuth client, the Python environment, and loading the Chrome extension with its native messaging host.

## Tech

JavaScript (Chrome extension), Python (native host, transcript fetching, Claude API, Google Drive API), macOS Keychain.
