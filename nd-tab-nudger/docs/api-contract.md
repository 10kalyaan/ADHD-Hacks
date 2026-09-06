# API Contract

Locked first, source of truth — keep in sync with the main build plan §6.

## `POST /ingest`

Request:
```json
{
  "tabId": 123,
  "title": "Reddit - Dive into anything",
  "url": "https://reddit.com/r/all",
  "domain": "reddit.com",
  "openedAt": 1730000000000
}
```

Response: `200 { "status": "ok", "label": "distraction" }`

## `POST /tabs/sync`

Sent by `background.js` on startup and whenever a tab closes. Deletes every
stored tab whose id isn't in the list, so closed tabs stop being ranked —
they're the oldest, so otherwise they dominate the staleness ranking and get
nudged even though they no longer exist. Reconciling the whole set (rather
than deleting one id at a time) also clears rows orphaned by a browser
restart, where `onRemoved` never fires.

Request:
```json
{ "openTabIds": [123, 456, 789] }
```

Response: `200 { "status": "ok", "removed": 2 }`

## `GET /nudge`

Response:
```json
{
  "cards": [
    {
      "tabId": 456,
      "title": "Q3 planning doc",
      "domain": "docs.google.com",
      "line": "This one's been waiting patiently. Suspiciously patiently.",
      "label": "work"
    },
    {
      "tabId": 789,
      "title": "React hooks guide",
      "domain": "reactjs.org",
      "line": "Still open from three hours ago. It's not going anywhere on its own.",
      "label": "reference"
    }
  ],
  "overlay_line": "Reddit again? Your Q3 doc says hi.",
  "open_tabs": [
    { "tabId": 111, "title": "Gmail", "domain": "mail.google.com", "openedAt": 1729999000000 }
  ]
}
```

`overlay_line` and `cards` share one endpoint so both the content script and
the New Tab page call the same thing.
