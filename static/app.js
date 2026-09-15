const form = document.getElementById("translate-form");
const input = document.getElementById("text-input");
const submitButton = form.querySelector("button");
const result = document.getElementById("result");
const video = document.getElementById("result-video");
const glossLine = document.getElementById("gloss-line");
const missingLine = document.getElementById("missing-line");
const status = document.getElementById("status");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;

  submitButton.disabled = true;
  status.textContent = "Translating...";
  result.hidden = true;

  try {
    const response = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await response.json();

    if (!response.ok) {
      status.textContent = data.error || "Something went wrong.";
      return;
    }

    glossLine.textContent = "ISL gloss: " + data.gloss.join(" ");

    if (data.missing && data.missing.length > 0) {
      missingLine.textContent = "No sign clip yet for: " + data.missing.join(", ");
      missingLine.hidden = false;
    } else {
      missingLine.hidden = true;
    }

    if (data.video_url) {
      video.src = data.video_url;
      video.hidden = false;
      video.load();
      video.play().catch(() => {});
    } else {
      video.hidden = true;
    }

    result.hidden = false;
    status.textContent = "";
  } catch (err) {
    status.textContent = "Request failed: " + err.message;
  } finally {
    submitButton.disabled = false;
  }
});
