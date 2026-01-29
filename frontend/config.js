import fs from "fs";
import os from "os";
import path from "path";

const CONFIG_PATHS = [
  path.join(os.homedir(), ".kachna.conf"),
  "/etc/kachna.conf",
];

const parseIni = (contents) => {
  const data = {};
  let section = null;

  for (const rawLine of contents.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || line.startsWith(";")) {
      continue;
    }

    const sectionMatch = line.match(/^\[([^\]]+)\]$/);
    if (sectionMatch) {
      section = sectionMatch[1].trim();
      if (!data[section]) {
        data[section] = {};
      }
      continue;
    }

    const keyMatch = line.match(/^([^=]+)=(.*)$/);
    if (!keyMatch || !section) {
      continue;
    }

    const key = keyMatch[1].trim();
    const value = keyMatch[2].trim();
    data[section][key] = value;
  }

  return data;
};

const mergeConfig = (base, next) => {
  for (const [section, values] of Object.entries(next)) {
    if (!base[section]) {
      base[section] = {};
    }
    Object.assign(base[section], values);
  }
};

const loadIniConfig = () => {
  const config = {};

  for (const configPath of CONFIG_PATHS) {
    if (!fs.existsSync(configPath)) {
      continue;
    }
    const contents = fs.readFileSync(configPath, "utf-8");
    mergeConfig(config, parseIni(contents));
  }

  return config;
};

const getConfigValue = (config, section, key) =>
  config?.[section]?.[key] ?? null;

export const loadFrontendConfig = () => {
  const config = loadIniConfig();
  return {
    apiUrl: getConfigValue(config, "frontend", "api_url"),
  };
};
