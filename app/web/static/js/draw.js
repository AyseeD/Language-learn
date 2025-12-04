const canvas = document.getElementById("drawCanvas");
const ctx = canvas.getContext("2d");

// ✅ INITIALIZE CANVAS WITH WHITE BACKGROUND
function initializeCanvas() {
  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.lineWidth = 12; // ✅ Thicker strokes for better model recognition
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = "#000000"; // ✅ Pure black strokes
}

initializeCanvas();

let drawing = false;
let lastX = 0;
let lastY = 0;
const undoStack = [];

function getCoordinates(e) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;

  if (e.touches) {
    // Touch event
    return {
      x: (e.touches[0].clientX - rect.left) * scaleX,
      y: (e.touches[0].clientY - rect.top) * scaleY
    };
  } else {
    // Mouse event
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  }
}

function startDrawing(e) {
  e.preventDefault();

  // Save current state for undo
  undoStack.push(ctx.getImageData(0, 0, canvas.width, canvas.height));
  document.getElementById("undoBtn").disabled = false;

  const coords = getCoordinates(e);
  lastX = coords.x;
  lastY = coords.y;
  drawing = true;

  // Draw a dot at the start point
  ctx.beginPath();
  ctx.arc(lastX, lastY, ctx.lineWidth / 2, 0, Math.PI * 2);
  ctx.fillStyle = "#000000";
  ctx.fill();
}

function draw(e) {
  e.preventDefault();
  if (!drawing) return;

  const coords = getCoordinates(e);

  ctx.beginPath();
  ctx.moveTo(lastX, lastY);
  ctx.lineTo(coords.x, coords.y);
  ctx.stroke();

  lastX = coords.x;
  lastY = coords.y;
}

function stopDrawing(e) {
  e.preventDefault();
  drawing = false;
}

function undo() {
  if (undoStack.length === 0) return;
  const imageData = undoStack.pop();
  ctx.putImageData(imageData, 0, 0);
  if (undoStack.length === 0) {
    document.getElementById("undoBtn").disabled = true;
  }
}

// Mouse events
canvas.addEventListener("mousedown", startDrawing);
canvas.addEventListener("mousemove", draw);
canvas.addEventListener("mouseup", stopDrawing);
canvas.addEventListener("mouseleave", stopDrawing);

// Touch events
canvas.addEventListener("touchstart", startDrawing);
canvas.addEventListener("touchmove", draw);
canvas.addEventListener("touchend", stopDrawing);
canvas.addEventListener("touchcancel", stopDrawing);

// Clear button
document.getElementById("clearBtn").addEventListener("click", () => {
  initializeCanvas();
  undoStack.length = 0;
  document.getElementById("undoBtn").disabled = true;
  document.getElementById("resultBox").style.display = "none";
});

// Undo button
document.getElementById("undoBtn").addEventListener("click", undo);

// ✅ IMPROVED: Better image preprocessing for model
function preprocessCanvasForModel() {
  // Create a square canvas (64x64) for better model input
  const size = 64;
  const exportCanvas = document.createElement("canvas");
  exportCanvas.width = size;
  exportCanvas.height = size;
  const exportCtx = exportCanvas.getContext("2d");

  // Fill with white background
  exportCtx.fillStyle = "white";
  exportCtx.fillRect(0, 0, size, size);

  // Calculate scaling to fit content within square while maintaining aspect ratio
  const scale = Math.min(size / canvas.width, size / canvas.height) * 0.8; // 0.8 for padding
  const scaledWidth = canvas.width * scale;
  const scaledHeight = canvas.height * scale;
  const offsetX = (size - scaledWidth) / 2;
  const offsetY = (size - scaledHeight) / 2;

  // Draw the canvas content centered and scaled
  exportCtx.drawImage(canvas, offsetX, offsetY, scaledWidth, scaledHeight);

  return exportCanvas.toDataURL("image/png");
}

// Submit button
document.getElementById("submitBtn").addEventListener("click", async () => {
  const resultBox = document.getElementById("resultBox");
  const predictedKanji = document.getElementById("predictedKanji");
  const confidenceEl = document.getElementById("confidence");
  const debugInfo = document.getElementById("debugInfo");

  // Check if canvas is empty
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const pixels = imageData.data;
  let isEmpty = true;

  for (let i = 0; i < pixels.length; i += 4) {
    // Check if any pixel is not white
    if (pixels[i] < 250 || pixels[i + 1] < 250 || pixels[i + 2] < 250) {
      isEmpty = false;
      break;
    }
  }

  if (isEmpty) {
    alert("Please draw something first!");
    return;
  }

  // Show loading state
  resultBox.style.display = "block";
  predictedKanji.textContent = "Analyzing...";
  confidenceEl.textContent = "...";
  debugInfo.innerHTML = "";

  try {
    console.log("📤 Submitting drawing...");

    const dataURL = preprocessCanvasForModel();

    const res = await fetch("/dashboard/kanji/predict", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ image: dataURL }),
    });

    if (!res.ok) {
      const errorText = await res.text();
      console.error("Server error:", errorText);
      throw new Error(`Server error: ${res.status}`);
    }

    const data = await res.json();
    console.log("📥 Received response:", data);

    if (!data.success) {
      throw new Error(data.error || "Prediction failed");
    }

    // Update UI with prediction
    predictedKanji.textContent = data.prediction.kanji || "?";
    confidenceEl.textContent = (data.prediction.confidence * 100).toFixed(1) + "%";

    // Show top 5 predictions if available
    if (data.prediction.debug_info?.top_5_predictions) {
      const top5 = data.prediction.debug_info.top_5_predictions;
      let debugHTML = '<div style="margin-top: 10px;"><strong>Top 5 predictions:</strong><br>';
      top5.forEach((pred, idx) => {
        debugHTML += `${idx + 1}. ${pred.kanji} (${(pred.confidence * 100).toFixed(1)}%)<br>`;
      });
      debugHTML += '</div>';
      debugInfo.innerHTML = debugHTML;
    }

  } catch (err) {
    predictedKanji.textContent = "Error";
    confidenceEl.textContent = "Could not predict";
    debugInfo.innerHTML = `<span style="color: red;">${err.message}</span>`;
    console.error("❌ Submission error:", err);
  }
});

// Prevent context menu on canvas
canvas.addEventListener("contextmenu", (e) => e.preventDefault());

console.log("✅ Canvas initialized successfully");