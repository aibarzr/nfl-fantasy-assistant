/** Content scripts host adapter lifecycle and UI rendering, never draft strategy. */

import {
  startEspnContentLifecycle,
  startSleeperContentLifecycle,
} from "./lifecycle.js";

export { detectEspnDraftSurface } from "../adapters/espn/surface.js";
export { detectSleeperDraftSurface } from "../adapters/sleeper/surface.js";
export { validateEspnPageMessage } from "./page-messages.js";
export {
  startEspnContentLifecycle,
  startSleeperContentLifecycle,
} from "./lifecycle.js";
export { renderRecommendations } from "./recommendations.js";
export { startSleeperLiveLoop } from "./sleeper-live-loop.js";

void startEspnContentLifecycle().then((panel) => {
  if (!panel) void startSleeperContentLifecycle();
});
