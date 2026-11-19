// Shared consent copy so the zoom-app and the Meet extension present the same
// wording. Keep dependency-free (plain ESM + sibling .d.ts).

export function buildConsentCopy(providerLabel) {
  return `Audio for this lecture will be processed via ${providerLabel}. No lecture data is shared without your consent.`;
}
