/**
 * Lightweight Node regression checks for CV autofill field mapping.
 * Run: node --experimental-strip-types lib/cv-autofill.test.mjs
 * (TypeScript source is mirrored here so CI without vitest can still verify the rules.)
 */

import assert from "node:assert/strict";

const AUTOFILL_MIN_CONFIDENCE = 0.6;

const CONFIDENCE_FOR_FIELD = {
  first_name: "name",
  last_name: "name",
  email: "email",
  phone: "phone",
  current_location: "location",
  current_company: "company",
  current_title: "title",
  total_experience_years: "experience",
};

function isConfident(data, formKey) {
  const confKey = CONFIDENCE_FOR_FIELD[formKey];
  if (!confKey) return false;
  const score = data.confidence?.[confKey];
  if (typeof score !== "number") return false;
  return score >= AUTOFILL_MIN_CONFIDENCE;
}

function parseToFormPatch(data) {
  const patch = {};
  if (data.first_name && isConfident(data, "first_name")) patch.first_name = data.first_name;
  if (data.last_name && isConfident(data, "last_name")) patch.last_name = data.last_name;
  if (data.email && isConfident(data, "email")) patch.email = data.email;
  if (data.phone && isConfident(data, "phone")) patch.phone = data.phone;
  if (data.current_location && isConfident(data, "current_location")) {
    patch.current_location = data.current_location;
  }
  if (data.current_company && isConfident(data, "current_company")) {
    patch.current_company = data.current_company;
  }
  if (data.current_title && isConfident(data, "current_title")) {
    patch.current_title = data.current_title;
  }
  if (data.total_experience_years != null && isConfident(data, "total_experience_years")) {
    patch.total_experience_years = String(data.total_experience_years);
  }
  if (data.linkedin_url) patch.linkedin_url = data.linkedin_url;
  return patch;
}

// Wrong values under the right keys must not autofill when confidence is low.
const badParse = {
  file_name: "cv.pdf",
  first_name: "Professional",
  last_name: "Summary",
  email: "john.smith@example.com",
  phone: "+91 98765 43210",
  current_location: "Mumbai",
  current_company: "Mumbai Port Digitization Platform",
  current_title: "Projects",
  total_experience_years: 8,
  linkedin_url: null,
  skills: [],
  confidence: {
    name: 0.2,
    email: 0.95,
    phone: 0.85,
    location: 0.3,
    company: 0.2,
    title: 0.2,
    experience: 0.7,
  },
};

const badPatch = parseToFormPatch(badParse);
assert.equal(badPatch.first_name, undefined, "low-confidence fake name must stay unmapped");
assert.equal(badPatch.last_name, undefined);
assert.equal(badPatch.current_location, undefined, "uncertain project city must stay unmapped");
assert.equal(badPatch.current_title, undefined, "Projects heading must stay unmapped");
assert.equal(badPatch.current_company, undefined);
assert.equal(badPatch.email, "john.smith@example.com");
assert.equal(badPatch.phone, "+91 98765 43210");

const goodParse = {
  file_name: "cv.pdf",
  first_name: "John",
  last_name: "Smith",
  email: "john.smith@example.com",
  phone: "+91 98765 43210",
  current_location: "Bengaluru",
  current_company: "Acme Corp",
  current_title: "Senior Engineer",
  total_experience_years: 8,
  linkedin_url: "https://linkedin.com/in/johnsmith",
  skills: ["Python"],
  confidence: {
    name: 0.9,
    email: 0.95,
    phone: 0.85,
    location: 0.85,
    company: 0.75,
    title: 0.8,
    experience: 0.8,
  },
};

const goodPatch = parseToFormPatch(goodParse);
assert.deepEqual(goodPatch, {
  first_name: "John",
  last_name: "Smith",
  email: "john.smith@example.com",
  phone: "+91 98765 43210",
  current_location: "Bengaluru",
  current_company: "Acme Corp",
  current_title: "Senior Engineer",
  total_experience_years: "8",
  linkedin_url: "https://linkedin.com/in/johnsmith",
});

console.log("cv-autofill.test.mjs: ok");
