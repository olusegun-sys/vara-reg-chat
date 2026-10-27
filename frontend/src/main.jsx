import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

// The React entry point.
// Why StrictMode: it surfaces bugs early by double-invoking certain functions in dev.
// It has no effect in production builds.
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);