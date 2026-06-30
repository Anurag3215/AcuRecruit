/* ==========================================================================
   AcuRecruit — Frontend interactions (pure client-side, no backend calls)
   ========================================================================== */

document.addEventListener("DOMContentLoaded", function () {

  /* ---- Password visibility toggle ---- */
  document.querySelectorAll(".toggle-password").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var input = btn.parentElement.querySelector("input");
      if (!input) return;
      var isHidden = input.type === "password";
      input.type = isHidden ? "text" : "password";
      btn.innerHTML = isHidden
        ? '<i class="fa-solid fa-eye-slash"></i>'
        : '<i class="fa-solid fa-eye"></i>';
    });
  });

  /* ---- Animated counters for stat cards ---- */
  document.querySelectorAll(".stat-num[data-count]").forEach(function (el) {
    var target = parseFloat(el.getAttribute("data-count")) || 0;
    var isDecimal = target % 1 !== 0;
    var duration = 900;
    var start = null;

    function step(timestamp) {
      if (!start) start = timestamp;
      var progress = Math.min((timestamp - start) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      var current = target * eased;
      el.textContent = isDecimal ? current.toFixed(1) : Math.round(current);
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = isDecimal ? target.toFixed(1) : target;
    }
    requestAnimationFrame(step);
  });

  /* ---- Live client-side table search (does not touch server data) ---- */
  document.querySelectorAll("[data-table-search]").forEach(function (input) {
    var tableId = input.getAttribute("data-table-search");
    var table = document.getElementById(tableId);
    if (!table) return;
    input.addEventListener("input", function () {
      var query = input.value.trim().toLowerCase();
      table.querySelectorAll("tbody tr").forEach(function (row) {
        var match = row.textContent.toLowerCase().indexOf(query) !== -1;
        row.style.display = match ? "" : "none";
      });
    });
  });

  /* ---- Drag & drop visual feedback for upload boxes ---- */
  document.querySelectorAll(".upload-box").forEach(function (box) {
    var fileInput = box.querySelector('input[type="file"]');
    var nameDisplay = box.querySelector(".upload-filenames");

    ["dragenter", "dragover"].forEach(function (evt) {
      box.addEventListener(evt, function (e) {
        e.preventDefault();
        box.classList.add("drag-active");
      });
    });
    ["dragleave", "drop"].forEach(function (evt) {
      box.addEventListener(evt, function (e) {
        e.preventDefault();
        box.classList.remove("drag-active");
      });
    });
    box.addEventListener("drop", function (e) {
      if (fileInput && e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        updateFileNames();
      }
    });

    function updateFileNames() {
      if (!fileInput || !nameDisplay) return;
      var files = fileInput.files;
      if (files.length === 0) {
        nameDisplay.textContent = "";
      } else if (files.length === 1) {
        nameDisplay.textContent = "Selected: " + files[0].name;
      } else {
        nameDisplay.textContent = files.length + " files selected";
      }
    }

    if (fileInput) {
      fileInput.addEventListener("change", updateFileNames);
    }
  });

  /* ---- Scroll-reveal for cards (subtle, one-time) ---- */
  if ("IntersectionObserver" in window) {
    var revealEls = document.querySelectorAll(".card, .stat-card");
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("slide-up");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08 }
    );
    revealEls.forEach(function (el) { observer.observe(el); });
  }

  /* ---- Button loading state on form submit (visual only) ---- */
  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function () {
      var submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.disabled) {
        submitBtn.dataset.originalHtml = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
        submitBtn.disabled = true;
      }
    });
  });
});
