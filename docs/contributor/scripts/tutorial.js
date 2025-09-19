// FastASGI Tutorial Shared JavaScript

// Smooth scrolling for navigation links
function initializeNavigation() {
  document
    .querySelectorAll('.sidebar a[href^="#"], .right-sidebar a[href^="#"]')
    .forEach((link) => {
      link.addEventListener("click", function (e) {
        e.preventDefault();
        const targetId = this.getAttribute("href").substring(1);
        const targetElement = document.getElementById(targetId);
        if (targetElement) {
          targetElement.scrollIntoView({ behavior: "smooth" });
        }
      });
    });
}

// Highlight current section in navigation
function initializeScrollSpy() {
  window.addEventListener("scroll", function () {
    const sections = document.querySelectorAll("h1[id], h2[id], h3[id]");
    const navLinks = document.querySelectorAll(
      '.sidebar a[href^="#"], .right-sidebar a[href^="#"]'
    );

    let current = "";
    sections.forEach((section) => {
      const rect = section.getBoundingClientRect();
      if (rect.top <= 100) {
        current = section.getAttribute("id");
      }
    });

    navLinks.forEach((link) => {
      link.classList.remove("active");
      if (link.getAttribute("href") === "#" + current) {
        link.classList.add("active");
      }
    });
  });
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  initializeNavigation();
  initializeScrollSpy();
  initializeFontSizeControls();
});

// Font size controls for content area
function initializeFontSizeControls() {
  const contentArea = document.querySelector(".content");
  if (!contentArea) return;

  // Get saved font size from localStorage or use default
  const savedSize = localStorage.getItem("tutorial-font-size");
  let currentFontSize = savedSize ? parseInt(savedSize) : 16;

  // Apply saved font size using style property
  if (contentArea instanceof HTMLElement) {
    contentArea.style.fontSize = currentFontSize + "px";
  }

  // Create font size controls container
  const fontControls = document.createElement("div");
  fontControls.className = "font-size-controls";
  fontControls.innerHTML = `
    <button class="font-btn" id="font-decrease" title="Decrease text size" aria-label="Decrease text size">A−</button>
    <button class="font-btn" id="font-increase" title="Increase text size" aria-label="Increase text size">A+</button>
  `;

  // Insert controls at the top of content area
  contentArea.insertBefore(fontControls, contentArea.firstChild);

  // Get references to controls with proper casting
  const decreaseBtn = document.getElementById("font-decrease");
  const increaseBtn = document.getElementById("font-increase");

  // Early return if any controls are missing
  if (!decreaseBtn || !increaseBtn) return;

  // Function to update font size
  function updateFontSize(newSize) {
    currentFontSize = Math.max(12, Math.min(24, newSize)); // Limit between 12px and 24px

    // Update content area font size
    if (contentArea instanceof HTMLElement) {
      contentArea.style.fontSize = currentFontSize + "px";
    }

    // Save to localStorage
    localStorage.setItem("tutorial-font-size", currentFontSize.toString());

    // Update button states
    if (decreaseBtn instanceof HTMLButtonElement) {
      decreaseBtn.disabled = currentFontSize <= 12;
    }
    if (increaseBtn instanceof HTMLButtonElement) {
      increaseBtn.disabled = currentFontSize >= 24;
    }
  }

  // Add event listeners
  if (decreaseBtn) {
    decreaseBtn.addEventListener("click", () => {
      updateFontSize(currentFontSize - 2);
    });
  }

  if (increaseBtn) {
    increaseBtn.addEventListener("click", () => {
      updateFontSize(currentFontSize + 2);
    });
  }

  // Initial button state update
  updateFontSize(currentFontSize);
}
