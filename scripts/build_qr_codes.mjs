#!/usr/bin/env node
/**
 * Generate print-quality, local QR-code SVG files for every public Project Atlas entry.
 *
 * The codes are deliberately generated in the repository, not requested from an
 * external QR service. Each SVG embeds the target URL as accessible metadata so
 * the validation script can check it without needing to decode the image again.
 */

import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import QRCode from "qrcode";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptDir, "..");
const dataPath = path.join(root, "data", "projects.json");
const outputDir = path.join(root, "assets", "qr");

function fileStem(value) {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function escapeXml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function publicTarget(project) {
  const target = project.publicPage || project.repositoryUrl;
  try {
    const url = new URL(target);
    if (url.protocol !== "https:") throw new Error("The URL is not HTTPS");
  } catch (error) {
    throw new Error(`${project.name}: QR target is invalid (${error.message})`);
  }
  return target;
}

function addAccessibleMetadata(svg, project, target) {
  const heading = `Scannable QR code for ${project.title}`;
  const replacement = `<svg$1 data-project-atlas-target="${escapeXml(target)}"><title>${escapeXml(heading)}</title>`;
  const result = svg.replace(/<svg([^>]*)>/, replacement);
  if (result === svg) throw new Error(`${project.name}: QR SVG has no opening SVG element`);
  return result;
}

const raw = await readFile(dataPath, "utf8");
const data = JSON.parse(raw);
if (!Array.isArray(data.projects) || !data.projects.length) {
  throw new Error("data/projects.json has no project list");
}

await mkdir(outputDir, { recursive: true });
const seen = new Set();
for (const project of data.projects) {
  const stem = fileStem(project.name);
  if (!stem || seen.has(stem)) throw new Error(`Cannot make a unique QR filename for ${project.name}`);
  seen.add(stem);

  const target = publicTarget(project);
  const svg = await QRCode.toString(target, {
    type: "svg",
    errorCorrectionLevel: "M",
    margin: 1,
    color: { dark: "#000000", light: "#ffffff" },
  });
  const accessibleSvg = addAccessibleMetadata(svg, project, target);
  await writeFile(path.join(outputDir, `${stem}.svg`), accessibleSvg, "utf8");
}

console.log(`Generated ${seen.size} local scannable QR-code SVG files in ${path.relative(root, outputDir)}.`);
