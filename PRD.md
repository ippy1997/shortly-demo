# PRD: URL Shortener API

## Goal
People who share long URLs (in chat, docs, or apps) want a short, easy-to-paste link that reliably takes visitors back to the original destination. Today they have no such service. The first version gives any client a simple HTTP API to submit a long URL and receive a short code, and to follow that short code back to the original URL, with basic usage tracking and automatic link expiry.

## Users
- **API consumer (developer or automated system)**: sends a long URL and gets back a short code/URL; wants creation to be fast and predictable, wants to optionally choose their own memorable code, and wants to check how many times a link has been used.
- **Link visitor**: opens a short URL in a browser or client; wants to land on the original destination without noticing the redirect, or get a clear error if the link is gone.

No administrator or account-holder role exists in this version — see Constraints.

## First version
1. **Create a short link from a long URL.** A client submits a long URL. The service returns a short code and the full short URL. Works for: submitting `https://example.com/some/long/path?query=1` returns a response containing a short code (e.g. `abc123`) and the resolvable short URL.
2. **Redirect from a short code to the original URL.** A client requests the short code's URL (e.g. visits it in a browser or issues a GET). The service responds with a redirect to the exact original long URL. Works for: creating a link then requesting its code returns an HTTP redirect (302) whose target matches the original submitted URL exactly.
3. **Optional custom alias at creation time.** A client may propose their own short code instead of receiving an auto-generated one. Works for: submitting a long URL with a requested alias `my-link` creates a link reachable at that exact code; submitting a second URL with an already-used alias is rejected with a clear conflict error (409) and no new link is created.
4. **Reject invalid input.** Submitting something that is not a well-formed absolute URL (e.g. missing scheme, empty string) is rejected with a 400-level error and no link is created. Works for: a request with `"not a url"` as the long URL returns an error response, and no short code is generated for it.
5. **Automatic link expiry after 24 hours.** Every short link, however created, stops redirecting 24 hours after it was created. Works for: a link created more than 24 hours ago returns a "gone/not found" style error instead of a redirect, and the original URL is no longer served through that code.
6. **Unknown code handling.** Requesting a short code that was never created (and is not simply expired) returns a 404-style error, distinguishable from the expired case is not required, but a clear not-found response is required. Works for: requesting a random unused code returns a 404 and no redirect.
7. **Usage count per link.** The service tracks, for each short code, how many times it has been successfully followed (redirected). This count is retrievable through the API. Works for: following a short code three times and then querying the link's info shows a count of 3; a freshly created, unfollowed link shows a count of 0.
8. **Persistence across restarts.** Links, their expiry, and their usage counts survive the service being stopped and restarted. Works for: creating a link, restarting the service, and successfully redirecting through that same code afterward (if still within its 24-hour window).
9. **Automated test coverage of the above.** The main journey — create a link, redirect through it, see its usage count go up, see it expire, see invalid input and alias conflicts rejected — is covered by an automated test suite that runs without manual setup. Works for: running the test suite completes and all tests pass.

## Not in the first version
- User accounts, authentication, or per-user link ownership (explicitly: no auth in v1).
- Editing or manually deleting an existing short link before it expires.
- Configurable or per-link expiry duration — the 24-hour expiry is fixed and global for v1.
- Reusing/recycling an expired code for a new link.
- Rate limiting, abuse prevention, or spam/malware URL checking.
- Any user interface, browser extension, or QR code generation.
- Analytics beyond a raw usage count (no referrer, geography, timestamps-per-click, or device data).
- Bulk creation or import of URLs.
- Custom domains for short links.

## Constraints
- Built with **FastAPI**.
- Data stored in **SQLite**.
- Delivered with an automated **test suite**.
- No authentication is required to use the API (stated by developer).

## Success
- The full main journey (create → redirect → usage count increments → expiry takes effect → invalid input and alias conflicts are rejected) is exercised by automated tests, and the suite passes.
- A short link created through the API can be followed and lands on the exact original URL, every time, until it expires.
- A link stops redirecting once its 24-hour lifetime has elapsed.
- No numeric traffic, latency, or adoption targets were set for v1; none are assumed.

## Defaults applied
- **No authentication or API keys** — stated directly by developer.
- **Custom aliases and usage-count analytics are included in v1; fixed 24-hour expiry for every link** — stated directly by developer.
- **Redirect uses HTTP 302 (temporary redirect)**, not 301, since links expire and should not be permanently cached by browsers. If permanent-style caching is wanted later, this can change to 301.
- **Auto-generated codes are short alphanumeric strings (e.g. 6 characters)** with no guaranteed meaning. If shorter/longer or a specific alphabet is needed, this is easy to change.
- **Custom aliases are restricted to a safe character set (letters, digits, hyphen, underscore) with a reasonable length limit (e.g. 3–30 characters)**; anything outside that is treated as invalid input (case 4). If the developer wants free-form aliases, this default can be relaxed.
- **Expired codes are permanently retired, not freed for reuse.** If reuse of expired codes is wanted, storage and code-generation logic would need to account for it.
- **Usage count is exposed via a dedicated read endpoint for that code** (alongside or instead of returning it inline with the redirect, since a redirect response body isn't typically inspected by clients). If the developer wants the count returned differently (e.g. only in creation response, or via a separate stats path), that is a small change.
- **Single SQLite file, single running instance** — no distributed/multi-instance concurrency handling is assumed, since no scale target was given.
- **Test suite uses FastAPI's standard test-client approach (pytest-based)** — implied by "FastAPI... tests" and not further specified.

## Open questions
- Whether the not-found response should distinguish "never existed" from "expired" (different status codes/messages) — default applied: both are user-facing errors indicating the link can't be used, exact status code differences (404 vs 410) left to the builder as long as both are clearly non-2xx and non-redirect.
- Whether there is any expected traffic volume or response-time target for v1 — none given; no target assumed.
