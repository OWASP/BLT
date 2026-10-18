import { cronMatches } from "./cron.js";
import { JOBS } from "./jobs.js";

export function dueJobs(scheduledTime, jobs = JOBS) {
  const date = new Date(Math.floor(scheduledTime / 60000) * 60000);
  return jobs.filter((job) => cronMatches(job.cron, date));
}

export async function runJob(env, job, scheduledTime) {
  const target = env[job.binding];
  if (!target) return { job: job.name, ok: false, error: `missing binding ${job.binding}` };
  try {
    const response = await target.fetch("https://cron.internal/__scheduled", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-blt-cron-secret": env.CRON_SECRET || "",
      },
      body: JSON.stringify(job.task ? { cron: job.cron, scheduledTime, task: job.task } : { cron: job.cron, scheduledTime }),
    });
    const ok = response.ok;
    if (!ok) console.error(`${job.name}: /__scheduled answered ${response.status}`);
    return { job: job.name, ok, status: response.status };
  } catch (error) {
    console.error(`${job.name}: ${error && error.message}`);
    return { job: job.name, ok: false, error: String(error && error.message) };
  }
}

export default {
  async scheduled(controller, env, ctx) {
    const jobs = dueJobs(controller.scheduledTime);
    ctx.waitUntil(Promise.all(jobs.map((job) => runJob(env, job, controller.scheduledTime))));
  },

  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      return Response.json({ ok: true, jobs: JOBS.map(({ name, cron, task }) => ({ name, cron, task })) });
    }
    return new Response("Not found", { status: 404 });
  },
};
