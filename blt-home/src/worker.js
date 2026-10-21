// blt-home Worker entry point. A module Worker may only export handlers, so the
// routing and the stats logic live in app.js and stats.js (both unit-tested).
import { handle } from "./app.js";

export default {
  fetch(request, env, ctx) {
    return handle(request, env, ctx);
  },
};
