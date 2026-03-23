import { createBrowserHostAdapter } from "./browserHost";
import type { SnapBackHostAdapter } from "./types";

export function createZoomHostAdapter(): SnapBackHostAdapter {
  const browserHost = createBrowserHostAdapter();
  return {
    ...browserHost,
    kind: "zoom-app",
    label: "Zoom App",
    capabilities: {
      ...browserHost.capabilities,
      nativeMeetingContext: true,
    },
    async getMeetingContext() {
      return {
        host: "zoom-app",
        label: "Zoom App",
        surface: "meeting-side-panel",
        meetingTitle: "Zoom meeting",
      };
    },
  };
}
