const APP_INDEX = new Map();

export function addApplication(name, location) {
  if (!name || !location) return;

  APP_INDEX.set(
    name.toLowerCase().trim(),
    location
  );
}

export function getApplication(name) {
  if (!name) return null;

  return (
    APP_INDEX.get(
      name.toLowerCase().trim()
    ) || null
  );
}

export function hasApplication(name) {
  return APP_INDEX.has(
    name.toLowerCase().trim()
  );
}

export function getAllApplications() {
  return [...APP_INDEX.entries()];
}

export function clearIndex() {
  APP_INDEX.clear();
}