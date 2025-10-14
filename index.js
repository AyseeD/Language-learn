import express from "express";
import axios from "axios";
import bodyParser from "body-parser";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";
import FormData from "form-data";


const app = express();
const port = 3000;

// Fix for __dirname in ES module scope
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

app.use(express.static(path.join(__dirname, "public")));
app.use(bodyParser.urlencoded({extended: true}));
app.use(bodyParser.json({ limit: "20mb" }));
app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

app.get("/", (req,res)=>{
    res.render("main.ejs");
});

app.get("/login", (req, res)=>{
    res.render("login.ejs");
});

app.get("/enter", (req,res)=>{
    res.render("hub.ejs");
})

app.get("/japan", (req,res)=>{
    res.render("japan.ejs");
})

// POST endpoint to receive the drawing
app.post("/submit-drawing", async (req, res) => {
  try {
    const imgData = req.body.image;
    if (!imgData || !imgData.startsWith("data:image/png;base64,")) {
      return res.status(400).send("Invalid image data");
    }

    const base64Data = imgData.replace(/^data:image\/png;base64,/, "");
    const uploadsDir = path.join(__dirname, "public", "uploads");
    fs.mkdirSync(uploadsDir, { recursive: true });

    const filename = `drawing-${Date.now()}.png`;
    const filePath = path.join(uploadsDir, filename);
    fs.writeFileSync(filePath, base64Data, "base64");
    console.log("Saved drawing to", filePath);

    // Send to Python API for prediction
    const formData = new FormData();
    formData.append("file", fs.createReadStream(filePath));

    const response = await axios.post("http://localhost:5001/predict", formData, {
      headers: formData.getHeaders(),
    });

    // Combine local URL + prediction result
    res.json({
      url: `/uploads/${filename}`,
      prediction: response.data,
    });

  } catch (err) {
    console.error("Error in /submit-drawing:", err);
    res.status(500).send("Server error saving or predicting image");
  }
});


app.listen(port, ()=>{
    console.log(`Listening to port: ${port}`);
});