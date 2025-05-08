import express from "express";
import axios from "axios";
import bodyParser from "body-parser";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

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

app.get("/", (req, res) => res.render(titles.main));
app.get("/draw", (req, res) => res.render(titles.draw));

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
app.post("/submit-drawing", (req, res) => {
    try {
      const imgData = req.body.image;
      if (!imgData || !imgData.startsWith("data:image/png;base64,")) {
        return res.status(400).send("Invalid image data");
      }
  
      // strip off the data-URI prefix to get just the base64-encoded bytes
      const base64Data = imgData.replace(/^data:image\/png;base64,/, "");
  
      // ensure the uploads folder exists
      const uploadsDir = path.join(__dirname, "public", "uploads");
      fs.mkdirSync(uploadsDir, { recursive: true });
  
      // name file with timestamp (or use uuid)
      const filename = `drawing-${Date.now()}.png`;
      const filePath = path.join(uploadsDir, filename);
  
      // write the binary file
      fs.writeFileSync(filePath, base64Data, "base64");
      console.log("Saved drawing to", filePath);
  
      // respond with the URL where the image is now accessible
      res.json({ url: `/uploads/${filename}` });
    } catch (err) {
      console.error("Error in /submit-drawing:", err);
      res.status(500).send("Server error saving image");
    }
  });
  

app.listen(port, ()=>{
    console.log(`Listening to port: ${port}`);
});