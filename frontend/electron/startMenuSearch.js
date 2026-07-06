import fs from "fs";
import path from "path";
import os from "os";

const START_MENU_PATHS = [
  path.join(
    process.env.ProgramData,
    "Microsoft",
    "Windows",
    "Start Menu",
    "Programs"
  ),

  path.join(
    os.homedir(),
    "AppData",
    "Roaming",
    "Microsoft",
    "Windows",
    "Start Menu",
    "Programs"
  ),
];

function scan(directory, files = []) {
  if (!fs.existsSync(directory))
    return files;

  const items = fs.readdirSync(directory);

  for (const item of items) {

    const fullPath = path.join(directory, item);

    const stat = fs.statSync(fullPath);

    if (stat.isDirectory()) {

      scan(fullPath, files);

    } else {

      files.push(fullPath);

    }
  }

  return files;
}

export function searchStartMenu(appName) {

  const keyword = appName
    .toLowerCase()
    .trim();

  let bestMatch = null;

  for (const directory of START_MENU_PATHS) {

    const files = scan(directory);

    for (const file of files) {

      if (!file.toLowerCase().endsWith(".lnk"))
        continue;

      const filename = path
        .basename(file)
        .toLowerCase();

      // Exact Match
      if (filename === `${keyword}.lnk`)
        return file;

      // Contains Match
      if (filename.includes(keyword)) {
        bestMatch = file;
      }

    }

  }

  return bestMatch;
}