import { createBrowserHostAdapter } from "./browserHost";
import type { SnapBackHostAdapter } from "./types";

export function createTeamsHostAdapter(): SnapBackHostAdapter {
  const browserHost = createBrowserHostAdapter();
  return {
    ...browserHost,
    kind: "teams-app",
    label: "Microsoft Teams App",
    capabilities: {
      ...browserHost.capabilities,
      nativeMeetingContext: true,
    },
    async getMeetingContext() {
      return {
        host: "teams-app",
        label: "Microsoft Teams App",
        surface: "meeting-side-panel",
        meetingTitle: "Microsoft Teams meeting",
      };
    },
  };
}
