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

    console.log("Received image data, length:", imgData.length);

    // Send base64 directly to Flask (bypass file upload issues)
    const response = await axios.post("http://localhost:5001/predict-base64", {
      image: imgData
    });

    console.log("Received prediction:", response.data);

    res.json({
      prediction: response.data,
    });

  } catch (err) {
    console.error("Error in /submit-drawing:", err);
    res.status(500).send("Server error predicting image");
  }
});

app.listen(port, ()=>{
    console.log(`Listening to port: ${port}`);
});