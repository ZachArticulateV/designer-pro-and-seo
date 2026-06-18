# Privacy & Data Handling

This plugin is a set of skills, scripts, and data files that run **locally inside
your Claude Code session**. It is not a hosted service and has no servers of its
own. This document explains how it handles data so you can use it on client work
responsibly.

## What the plugin collects

**Nothing.** The plugin contains no telemetry, analytics, or "phone-home" code.
It does not transmit your prompts, files, API keys, or outputs anywhere on its
own.

## Credentials & API keys

Several skills can optionally call external services (Google APIs, DataForSEO,
Firecrawl, nanobanana image generation). When you use those:

- Provide credentials via **environment variables**, never hard-coded in files.
- Scripts must **never log API keys, tokens, or secrets** to stdout, files, or
  reports. (This is a hard rule enforced in `references/ENGINE-CONTRACTS.md`.)
- Any credential the plugin reads stays in your local environment; it is sent
  only to the service you configured, by that service's own client.

## Data you process

- **Scraped pages, crawl results, and reports** are written to your local
  project workspace only.
- **Lead lists / outreach data** (client-outreach skill) stay local. You are
  responsible for complying with anti-spam law (CAN-SPAM, GDPR, CASL) when you
  send anything.
- The plugin does not retain a copy of anything between sessions beyond the files
  it writes into your workspace at your direction.

## Third-party services

When you opt in to an external MCP/API, **that service's privacy policy and
terms govern the data you send it.** Review them — especially before sending
client URLs or content to crawlers/SERP APIs. Respect target sites' robots.txt
and Terms of Service when crawling.

## Your responsibility

Because this runs on your machine with your credentials on your clients' data,
you are the data controller. Use it within the agreements you have with your
clients and the law in your jurisdiction.

Questions: open an issue at
<https://github.com/ZachArticulateV/designer-pro-and-seo/issues>.
