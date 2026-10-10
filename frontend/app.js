const form = document.getElementById("generate-form");
const generateButton = document.getElementById("generate-button");
const statusEl = document.getElementById("status");
const activitySection = document.getElementById("activity");
const activityNoticeEl = document.getElementById("activity-notice");
const titleEl = document.getElementById("activity-title");
const durationEl = document.getElementById("activity-duration");
const descriptionEl = document.getElementById("activity-description");
const checklistEl = document.getElementById("checklist");
const tipEl = document.getElementById("activity-tip");
const missionTitleEl = document.getElementById("mission-title");
const missionDurationEl = document.getElementById("mission-duration");
const missionDescriptionEl = document.getElementById("mission-description");
const missionStepsEl = document.getElementById("mission-steps");
const missionStateEl = document.getElementById("mission-state");
const missionStatusEl = document.getElementById("mission-status");
const completeMissionButton = document.getElementById("complete-mission");
const anotherMissionButton = document.getElementById("another-mission");
const resetMissionButton = document.getElementById("reset-mission");
const missionCountEl = document.getElementById("mission-count");
const breakCountEl = document.getElementById("break-count");
const progressEmptyEl = document.getElementById("progress-empty");
const completeBreakButton = document.getElementById("complete-break");
const breakStatusEl = document.getElementById("break-complete-status");

const ALLOWED_DURATIONS = new Set(["5", "10", "15", "30"]);
const ALLOWED_ACTIVITIES = new Set([
  "Walking",
  "Gardening",
  "Birdwatching",
  "Nature Exploration",
]);
const ALLOWED_DIFFICULTIES = new Set(["Gentle", "Moderate", "Adventurous"]);

const DEFAULTS = {
  duration: "5",
  activity: "Walking",
  difficulty: "Gentle",
};

function readableText(value) {
  const named = { amp: "&", apos: "'", quot: '"', lt: "<", gt: ">", nbsp: " " };
  let text = String(value ?? "")
    .replace(/â€™|â€˜/g, "'")
    .replace(/â€œ|â€/g, '"')
    .replace(/â€”/g, "-")
    .replace(/â€“/g, "-")
    .replace(/\u00a0/g, " ");
  text = text.replace(/&(#x?[0-9a-f]+|[a-z]+);/gi, (entity, body) => {
    const lower = body.toLowerCase();
    if (lower.startsWith("#x")) {
      const code = Number.parseInt(lower.slice(2), 16);
      return Number.isFinite(code) ? String.fromCodePoint(code) : entity;
    }
    if (lower.startsWith("#")) {
      const code = Number.parseInt(lower.slice(1), 10);
      return Number.isFinite(code) ? String.fromCodePoint(code) : entity;
    }
    return Object.prototype.hasOwnProperty.call(named, lower) ? named[lower] : entity;
  });
  return text.replace(/[ \t]+/g, " ").trim();
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function selectedValue(name) {
  const field = form.elements.namedItem(name);
  const value = field && "value" in field ? field.value : "";
  return value || DEFAULTS[name];
}

function readFormValues() {
  const duration = selectedValue("duration");
  const activity = selectedValue("activity");
  const difficulty = selectedValue("difficulty");

  if (!ALLOWED_DURATIONS.has(duration)) {
    throw new Error("Please choose 5, 10, 15, or 30 minutes.");
  }
  if (!ALLOWED_ACTIVITIES.has(activity)) {
    throw new Error("Please choose a supported outdoor activity.");
  }
  if (!ALLOWED_DIFFICULTIES.has(difficulty)) {
    throw new Error("Please choose Gentle, Moderate, or Adventurous.");
  }

  return {
    duration_minutes: Number(duration),
    activity_type: activity,
    difficulty,
  };
}

let currentPlan = null;

function renderActivity(activity) {
  currentPlan = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    completed: false,
  };
  const minutes = activity.duration_minutes;
  titleEl.textContent = readableText(activity.title);
  durationEl.textContent = `Estimated duration: ${minutes} minutes`;
  descriptionEl.textContent = readableText(activity.description);
  checklistEl.replaceChildren();
  completeBreakButton.disabled = false;
  completeBreakButton.setAttribute("aria-disabled", "false");
  setBreakMessage("");
  const fallbackNotice =
    activity.source === "template-fallback"
      ? readableText(activity.notice) ||
        "This plan came from the built-in templates, not from the local model."
      : "";
  activityNoticeEl.textContent = fallbackNotice;
  activityNoticeEl.hidden = !fallbackNotice;

  activity.steps.forEach((step) => {
    const item = document.createElement("li");
    item.textContent = readableText(step);
    checklistEl.append(item);
  });

  tipEl.replaceChildren();
  const tipLabel = document.createElement("strong");
  tipLabel.textContent = "Tip: ";
  tipEl.append(tipLabel, document.createTextNode(readableText(activity.tip)));

  activitySection.hidden = false;
  activitySection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function parseError(payload, fallback) {
  if (!payload) {
    return fallback;
  }
  const detail = payload.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail) && detail.length) {
    return "Choose a duration, an outdoor activity, and an adventure level, then try again.";
  }
  if (detail && detail.error) {
    return detail.hint ? `${detail.error} ${detail.hint}` : detail.error;
  }
  return fallback;
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      setStatus("The break planner is still starting. Refresh in a moment.", true);
    }
  } catch {
    setStatus(
      "Could not reach the GreenBreak AI server. Start the FastAPI app and refresh.",
      true
    );
  }
}

checkHealth();

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  let payload;
  try {
    payload = readFormValues();
  } catch (error) {
    setStatus(error.message, true);
    return;
  }

  generateButton.disabled = true;
  setStatus("Asking the local model for your outdoor break plan...");

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(
        parseError(data, "The break plan could not be created. Please try again.")
      );
    }

    if (
      !data.title ||
      !data.description ||
      !data.tip ||
      !data.duration_minutes ||
      !Array.isArray(data.steps) ||
      data.steps.length === 0
    ) {
      throw new Error("The server did not return a complete break plan.");
    }

    renderActivity(data);
    if (data.source === "template-fallback") {
      setStatus(
        activityNoticeEl.textContent ||
          "This plan came from the built-in templates, not from the local model."
      );
    } else {
      setStatus("Your break plan is ready. Step outside when you can.");
    }
  } catch (error) {
    activitySection.hidden = true;
    currentPlan = null;
    setStatus(error.message, true);
  } finally {
    generateButton.disabled = false;
  }
});

const MISSIONS = [
  {
    id: "nature-walk",
    title: "Take a short nature walk",
    description:
      "Leave the screen for a short walk near trees, a park edge, or a quiet street. The mission is finished once you have been outside and noticed the place around you.",
    duration: "10 minutes",
    steps: [
      "Step outside and leave your screen indoors.",
      "Walk slowly toward the nearest trees, park, or green street.",
      "Notice one sound, one color, and one living thing before you turn back.",
    ],
  },
  {
    id: "three-plants",
    title: "Observe three different plants",
    description:
      "A close look at three plants is enough to pull your attention outdoors. Stay near home and give each plant a moment of real attention.",
    duration: "10 minutes",
    steps: [
      "Find three different plants within a short walk of your door.",
      "Look at the leaves, stems, or flowers of each one.",
      "Name one difference between them before you go back inside.",
    ],
  },
  {
    id: "listen-birds",
    title: "Listen to the birds",
    description:
      "Stand still long enough to hear what is already outside. You do not need to travel or identify every call.",
    duration: "8 minutes",
    steps: [
      "Step outside and stand or sit where you can see branches and sky.",
      "Stay quiet and listen for bird calls or wing movement.",
      "Wait until you notice one bird, or simply the quiet between sounds.",
    ],
  },
  {
    id: "care-for-plant",
    title: "Spend time caring for a plant",
    description:
      "Give one plant a little care. A pot, a window box, or a small garden patch all count.",
    duration: "10 minutes",
    steps: [
      "Choose one plant, pot, or small patch of soil.",
      "Water it, remove a few dead leaves, or gently tidy the soil.",
      "Look at the plant once more, then stop while the task still feels small.",
    ],
  },
  {
    id: "sky-pause",
    title: "Watch the sky for a quiet pause",
    description:
      "A few minutes of open sky rests your eyes and marks a clean break from the screen.",
    duration: "5 minutes",
    steps: [
      "Go somewhere you can see a patch of sky.",
      "Watch the clouds, light, or birds without checking a screen.",
      "Take three slow breaths, then head back in.",
    ],
  },
  {
    id: "green-edge",
    title: "Find one nearby patch of green",
    description:
      "Search out the closest bit of nature you can reach on foot, then spend the break there.",
    duration: "15 minutes",
    steps: [
      "Walk to the nearest lawn, garden, trail, or tree-lined block.",
      "Stay there long enough to notice the ground, the plants, and the air.",
      "Turn back with enough time to return without rushing.",
    ],
  },
];

const MISSION_STORAGE_KEY = "greenbreak.todayMission";

function todayKey(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function dailyMissionIndex(date = new Date()) {
  const utc = Date.UTC(date.getFullYear(), date.getMonth(), date.getDate());
  const dayNumber = Math.floor(utc / 86400000);
  return dayNumber % MISSIONS.length;
}

function missionById(id) {
  return MISSIONS.find((mission) => mission.id === id) || null;
}

function readSavedMission() {
  try {
    const raw = localStorage.getItem(MISSION_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const saved = JSON.parse(raw);
    if (!saved || saved.date !== todayKey() || !missionById(saved.missionId)) {
      return null;
    }
    return {
      date: saved.date,
      missionId: saved.missionId,
      completed: Boolean(saved.completed),
    };
  } catch {
    return null;
  }
}

function writeSavedMission(state) {
  localStorage.setItem(MISSION_STORAGE_KEY, JSON.stringify(state));
}

let missionState = readSavedMission() || {
  date: todayKey(),
  missionId: MISSIONS[dailyMissionIndex()].id,
  completed: false,
};

function setMissionMessage(message) {
  missionStatusEl.textContent = message || "";
  missionStatusEl.hidden = !message;
}

function renderMission() {
  const mission = missionById(missionState.missionId) || MISSIONS[dailyMissionIndex()];
  missionState.missionId = mission.id;
  missionTitleEl.textContent = readableText(mission.title);
  missionDurationEl.textContent = `Estimated duration: ${mission.duration}`;
  missionDescriptionEl.textContent = readableText(mission.description);
  missionStepsEl.replaceChildren();
  mission.steps.forEach((step) => {
    const item = document.createElement("li");
    item.textContent = readableText(step);
    missionStepsEl.append(item);
  });

  missionStateEl.textContent = missionState.completed ? "Completed" : "Not completed";
  missionStateEl.classList.toggle("is-complete", missionState.completed);
  completeMissionButton.disabled = missionState.completed;
  completeMissionButton.setAttribute("aria-disabled", String(missionState.completed));
}

function missionCountKey() {
  return `${todayKey()}:${missionState.missionId}`;
}

function completeMission() {
  const key = missionCountKey();
  if (missionState.completed || progress.countedMissionKeys.includes(key)) {
    missionState = { ...missionState, date: todayKey(), completed: true };
    writeSavedMission(missionState);
    renderMission();
    setMissionMessage("This mission is already complete.");
    return;
  }

  completeMissionButton.disabled = true;
  missionState = { ...missionState, date: todayKey(), completed: true };
  writeSavedMission(missionState);
  progress.completedMissions += 1;
  progress.countedMissionKeys.push(key);
  writeProgress(progress);
  renderProgress();
  renderMission();
  setMissionMessage("Mission complete. You finished today's outdoor mission.");
}

function startAnotherMission() {
  const currentIndex = MISSIONS.findIndex((mission) => mission.id === missionState.missionId);
  const next = MISSIONS[(currentIndex + 1) % MISSIONS.length];
  missionState = { date: todayKey(), missionId: next.id, completed: false };
  writeSavedMission(missionState);
  renderMission();
  setMissionMessage("Here is another mission for today.");
}

function resetMission() {
  const daily = MISSIONS[dailyMissionIndex()];
  const alreadyDaily = missionState.missionId === daily.id && !missionState.completed;
  const key = `${todayKey()}:${daily.id}`;
  progress.countedMissionKeys = progress.countedMissionKeys.filter((item) => item !== key);
  writeProgress(progress);
  missionState = { date: todayKey(), missionId: daily.id, completed: false };
  writeSavedMission(missionState);
  renderMission();
  setMissionMessage(
    alreadyDaily
      ? "This is already today's mission."
      : "Today's mission is reset. You can complete it again."
  );
}

renderMission();
if (missionState.completed) {
  setMissionMessage("Today's mission is already complete.");
}

completeMissionButton.addEventListener("click", completeMission);
anotherMissionButton.addEventListener("click", startAnotherMission);
resetMissionButton.addEventListener("click", resetMission);

const PROGRESS_STORAGE_KEY = "greenbreak.progress";

function emptyProgress() {
  return {
    completedMissions: 0,
    completedBreaks: 0,
    countedMissionKeys: [],
    countedBreakIds: [],
  };
}

function stringList(value) {
  return Array.isArray(value) ? value.filter((item) => typeof item === "string") : [];
}

function readProgress() {
  try {
    const raw = localStorage.getItem(PROGRESS_STORAGE_KEY);
    if (!raw) {
      return emptyProgress();
    }
    const saved = JSON.parse(raw);
    const completedMissions = Number(saved.completedMissions);
    const completedBreaks = Number(saved.completedBreaks);
    if (!Number.isInteger(completedMissions) || completedMissions < 0) {
      return emptyProgress();
    }
    if (!Number.isInteger(completedBreaks) || completedBreaks < 0) {
      return emptyProgress();
    }
    return {
      completedMissions,
      completedBreaks,
      countedMissionKeys: stringList(saved.countedMissionKeys),
      countedBreakIds: stringList(saved.countedBreakIds),
    };
  } catch {
    return emptyProgress();
  }
}

function writeProgress(state) {
  localStorage.setItem(PROGRESS_STORAGE_KEY, JSON.stringify(state));
}

let progress = readProgress();

function renderProgress() {
  missionCountEl.textContent = String(progress.completedMissions);
  breakCountEl.textContent = String(progress.completedBreaks);
  const isEmpty = progress.completedMissions === 0 && progress.completedBreaks === 0;
  progressEmptyEl.hidden = !isEmpty;
}

function setBreakMessage(message) {
  breakStatusEl.textContent = message || "";
  breakStatusEl.hidden = !message;
}

function markBreakComplete() {
  if (!currentPlan || activitySection.hidden) {
    setBreakMessage("Generate a break plan before marking it complete.");
    return;
  }
  if (currentPlan.completed || progress.countedBreakIds.includes(currentPlan.id)) {
    currentPlan.completed = true;
    completeBreakButton.disabled = true;
    completeBreakButton.setAttribute("aria-disabled", "true");
    setBreakMessage("This break is already complete.");
    return;
  }

  currentPlan.completed = true;
  completeBreakButton.disabled = true;
  completeBreakButton.setAttribute("aria-disabled", "true");
  progress.completedBreaks += 1;
  progress.countedBreakIds.push(currentPlan.id);
  if (progress.countedBreakIds.length > 40) {
    progress.countedBreakIds = progress.countedBreakIds.slice(-40);
  }
  writeProgress(progress);
  renderProgress();
  setBreakMessage("Break complete. This plan has been added to your progress.");
}

renderProgress();
completeBreakButton.addEventListener("click", markBreakComplete);
