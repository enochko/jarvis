/**
 * Shared logging for all Jarvis services.
 *
 * File: <logDir>/<service>_YYYYMMDD.log at DEBUG, rotated at 5 MB (3 backups).
 * Console: INFO and above.
 */
import { appendFileSync, existsSync, mkdirSync, renameSync, rmSync, statSync } from "node:fs";
import { join } from "node:path";

const LEVELS = { DEBUG: 10, INFO: 20, WARNING: 30, ERROR: 40 };
const MAX_BYTES = 5 * 1024 * 1024;
const BACKUPS = 3;

function stamp(d = new Date()) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function dayStamp(d = new Date()) {
  return stamp(d).slice(0, 10).replaceAll("-", "");
}

function rotate(file) {
  try {
    if (!existsSync(file) || statSync(file).size < MAX_BYTES) return;
    rmSync(`${file}.${BACKUPS}`, { force: true });
    for (let i = BACKUPS - 1; i >= 1; i--) {
      if (existsSync(`${file}.${i}`)) renameSync(`${file}.${i}`, `${file}.${i + 1}`);
    }
    renameSync(file, `${file}.1`);
  } catch {
    // Rotation failure must never take a service down.
  }
}

/**
 * @param {string} service  e.g. "agent", "bot", "web"
 * @param {string} logDir
 */
export function createLogger(service, logDir) {
  let fileOk = true;
  try {
    mkdirSync(logDir, { recursive: true });
  } catch {
    fileOk = false;
  }

  function write(level, msg) {
    const line = `${stamp()} | ${level.padEnd(7)} | ${service.padEnd(5)} | ${msg}`;
    if (LEVELS[level] >= LEVELS.INFO) {
      (LEVELS[level] >= LEVELS.WARNING ? console.error : console.log)(line);
    }
    if (fileOk) {
      const file = join(logDir, `${service}_${dayStamp()}.log`);
      try {
        rotate(file);
        appendFileSync(file, line + "\n", "utf8");
      } catch {
        fileOk = false;
        console.error(`${stamp()} | WARNING | ${service} | log file not writable, console only`);
      }
    }
  }

  const logger = {
    debug: (m) => write("DEBUG", m),
    info: (m) => write("INFO", m),
    warn: (m) => write("WARNING", m),
    error: (m) => write("ERROR", m),
  };
  logger.info(`Logging initialised | service=${service} | log_dir=${logDir}`);
  return logger;
}
