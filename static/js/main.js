/**
 * Student Portal – Main JavaScript
 * Handles:
 *  - Dynamic population of select boxes via async fetch
 *  - Client-side form validation
 *  - File upload preview
 *  - Flash message auto-dismiss
 *  - Admission status async update
 */

/* ============================================================
   UTILITY HELPERS
   ============================================================ */

/**
 * Fetch JSON from a URL and return parsed data.
 * @param {string} url
 * @returns {Promise<any>}
 */
async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
  return res.json();
}

/**
 * Populate a <select> element with an array of option values.
 * @param {HTMLSelectElement} selectEl
 * @param {string[]} options
 * @param {string} placeholder - default empty option label
 */
function populateSelect(selectEl, options, placeholder = "Select an option") {
  // Clear existing options
  selectEl.innerHTML = `<option value="" disabled selected>${placeholder}</option>`;

  options.forEach((opt) => {
    const el = document.createElement("option");
    el.value = opt;
    el.textContent = opt;
    selectEl.appendChild(el);
  });
}

/* ============================================================
   DYNAMIC SELECT POPULATION
   Fetches options asynchronously from Flask API endpoints.
   ============================================================ */

/**
 * Load all dynamic select boxes on the form page.
 */
async function loadDynamicSelects() {
  try {
    // Run all fetches in parallel for speed
    const [programmes, countries, levels, entryYears] = await Promise.all([
      fetchJSON("/api/programmes"),
      fetchJSON("/api/countries"),
      fetchJSON("/api/levels"),
      fetchJSON("/api/entry_years"),
    ]);

    const selProgramme  = document.getElementById("programme");
    const selCountry    = document.getElementById("country");
    const selLevel      = document.getElementById("level");
    const selEntryYear  = document.getElementById("year_of_entry");

    if (selProgramme) populateSelect(selProgramme, programmes, "Select programme");
    if (selCountry)   populateSelect(selCountry,   countries,  "Select country");
    if (selLevel)     populateSelect(selLevel,      levels,     "Select level");
    if (selEntryYear) {
      // Entry years are numbers – show them as strings
      populateSelect(selEntryYear, entryYears.map(String), "Select year");
    }

  } catch (err) {
    console.error("Failed to load select options:", err);
  }
}

/* ============================================================
   FORM VALIDATION
   ============================================================ */

/**
 * Show an error message below a form control.
 * @param {HTMLElement} input
 * @param {string} message
 */
function showError(input, message) {
  input.classList.add("error");
  const errEl = input.parentElement.querySelector(".error-msg");
  if (errEl) {
    errEl.textContent = message;
    errEl.classList.add("show");
  }
}

/**
 * Clear the error state for a form control.
 * @param {HTMLElement} input
 */
function clearError(input) {
  input.classList.remove("error");
  const errEl = input.parentElement.querySelector(".error-msg");
  if (errEl) errEl.classList.remove("show");
}

/**
 * Validate the portal form before submission.
 * @param {HTMLFormElement} form
 * @returns {boolean} – true if valid
 */
function validateForm(form) {
  let valid = true;

  // All required inputs / selects / textareas
  const requiredFields = form.querySelectorAll("[required]");

  requiredFields.forEach((field) => {
    clearError(field);
    const value = field.value.trim();

    if (!value) {
      showError(field, "This field is required.");
      valid = false;
      return;
    }

    // Email format check
    if (field.type === "email") {
      const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRe.test(value)) {
        showError(field, "Please enter a valid email address.");
        valid = false;
      }
    }

    // GPA range check
    if (field.id === "gpa") {
      const gpa = parseFloat(value);
      if (isNaN(gpa) || gpa < 0 || gpa > 4.0) {
        showError(field, "GPA must be between 0.0 and 4.0.");
        valid = false;
      }
    }
  });

  // File upload check (not marked as 'required' in HTML to avoid ugly browser UI)
  const photoInput = form.querySelector("#photo");
  if (photoInput && !photoInput.files.length) {
    const wrapper = photoInput.closest(".file-upload-wrapper");
    const label   = wrapper.querySelector(".file-upload-label");
    label.style.borderColor = "var(--error)";
    label.style.background  = "#FEF2F2";

    // Create or reuse error paragraph
    let errPara = wrapper.querySelector(".error-msg");
    if (!errPara) {
      errPara = document.createElement("p");
      errPara.className = "error-msg";
      wrapper.appendChild(errPara);
    }
    errPara.textContent = "Please upload a profile photo.";
    errPara.classList.add("show");
    valid = false;
  }

  // Radio buttons – at least one gender must be selected
  const genderRadios = form.querySelectorAll('input[name="gender"]');
  const genderChecked = [...genderRadios].some((r) => r.checked);
  if (!genderChecked) {
    const genderGroup = form.querySelector(".gender-error");
    if (genderGroup) {
      genderGroup.textContent = "Please select a gender.";
      genderGroup.classList.add("show");
    }
    valid = false;
  }

  return valid;
}

/* ============================================================
   FILE UPLOAD PREVIEW
   ============================================================ */

/**
 * Set up the file input to show the chosen filename and
 * optionally a small image preview.
 */
function setupFileUpload() {
  const photoInput = document.getElementById("photo");
  if (!photoInput) return;

  const label      = document.querySelector(".file-upload-label");
  const nameDisplay = document.querySelector(".file-name-display");

  photoInput.addEventListener("change", () => {
    const file = photoInput.files[0];
    if (!file) return;

    // Show filename
    if (nameDisplay) nameDisplay.textContent = `✓ ${file.name}`;

    // Reset any error styling on the label
    if (label) {
      label.style.borderColor = "var(--success)";
      label.style.background  = "#F0FDF4";
    }

    // Clear file error message
    const wrapper = photoInput.closest(".file-upload-wrapper");
    const errPara  = wrapper && wrapper.querySelector(".error-msg");
    if (errPara) errPara.classList.remove("show");
  });
}

/* ============================================================
   FLASH MESSAGES – Auto-dismiss
   ============================================================ */

/**
 * Dismiss a flash message element with a fade-out.
 * @param {HTMLElement} flashEl
 */
function dismissFlash(flashEl) {
  flashEl.style.transition = "opacity 0.4s ease, transform 0.4s ease";
  flashEl.style.opacity    = "0";
  flashEl.style.transform  = "translateX(30px)";
  setTimeout(() => flashEl.remove(), 400);
}

/**
 * Initialise all flash messages: click-to-dismiss + auto-dismiss.
 */
function initFlashMessages() {
  document.querySelectorAll(".flash").forEach((el, idx) => {
    // Click to dismiss
    el.addEventListener("click", () => dismissFlash(el));

    // Auto-dismiss after 5 seconds (staggered by index)
    setTimeout(() => {
      if (el.isConnected) dismissFlash(el);
    }, 5000 + idx * 500);
  });
}

/* ============================================================
   ADMISSION STATUS – Async Update (Detail Page)
   ============================================================ */

/**
 * Send a PATCH/POST request to update the student's admission status
 * and show inline feedback without a page reload.
 * @param {number} studentId
 */
function initStatusUpdate(studentId) {
  const btn      = document.getElementById("update-status-btn");
  const select   = document.getElementById("admission_status");
  const feedback = document.getElementById("status-feedback");

  if (!btn || !select) return;

  btn.addEventListener("click", async () => {
    const newStatus = select.value;
    if (!newStatus) return;

    btn.disabled    = true;
    btn.textContent = "Updating…";
    feedback.className      = "status-feedback";
    feedback.style.display  = "none";

    try {
      const res = await fetch(`/update_status/${studentId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });

      const data = await res.json();

      if (data.success) {
        feedback.textContent = `✓ Status updated to "${data.status}"`;
        feedback.className   = "status-feedback success";
        feedback.style.display = "inline-block";

        // Update the badge on the page if it exists
        const badge = document.getElementById("current-status-badge");
        if (badge) {
          badge.textContent = data.status;
          badge.className   = `badge badge-${data.status.toLowerCase()}`;
        }
      } else {
        throw new Error(data.message || "Unknown error");
      }
    } catch (err) {
      feedback.textContent = `✗ Update failed: ${err.message}`;
      feedback.className   = "status-feedback error";
      feedback.style.display = "inline-block";
    } finally {
      btn.disabled    = false;
      btn.textContent = "Update";

      // Hide feedback after 3 s
      setTimeout(() => {
        feedback.style.display = "none";
      }, 3500);
    }
  });
}

/* ============================================================
   FORM SUBMISSION HANDLER
   ============================================================ */

function initPortalForm() {
  const form = document.getElementById("portal-form");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    // Clear all errors first, then revalidate
    form.querySelectorAll(".form-control").forEach(clearError);

    const isValid = validateForm(form);

    if (!isValid) {
      e.preventDefault();
      // Scroll to first error
      const firstError = form.querySelector(".error, .error-msg.show");
      if (firstError) {
        firstError.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      return;
    }

    // Show loading state on button
    const submitBtn = form.querySelector('[type="submit"]');
    if (submitBtn) {
      submitBtn.classList.add("btn-loading");
      submitBtn.textContent = "Submitting…";
    }
  });

  // Live validation – clear error on user input
  form.querySelectorAll(".form-control").forEach((input) => {
    input.addEventListener("input", () => clearError(input));
    input.addEventListener("change", () => clearError(input));
  });
}

/* ============================================================
   DOMContentLoaded – Entry point
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  initFlashMessages();
  loadDynamicSelects();
  setupFileUpload();
  initPortalForm();

  // Detail page: read student ID from data attribute on body
  const studentId = document.body.dataset.studentId;
  if (studentId) {
    initStatusUpdate(parseInt(studentId, 10));
  }

  // Mark active nav link
  const currentPath = window.location.pathname;
  document.querySelectorAll(".nav-links a").forEach((link) => {
    if (link.getAttribute("href") === currentPath) {
      link.classList.add("active");
    }
  });
});
