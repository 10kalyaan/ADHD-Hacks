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
