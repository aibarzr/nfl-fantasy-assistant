/** Content scripts host adapter lifecycle and UI rendering, never draft strategy. */

import { startEspnContentLifecycle } from "./lifecycle.js";

export { detectEspnDraftSurface } from "../adapters/espn/surface.js";
export { validateEspnPageMessage } from "./page-messages.js";
export { startEspnContentLifecycle } from "./lifecycle.js";
export { renderRecommendations } from "./recommendations.js";

void startEspnContentLifecycle();
