// The time/duration formatters live in the shared package so the zoom-app and
// the Meet extension stay in sync. Re-exported here so existing `./utils`
// imports keep working.
export { formatDuration, formatTimestamp } from "@snapback/shared";
