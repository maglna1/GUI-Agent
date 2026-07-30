import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import iconUrl from "../assets/icon/tpsp_icon.png?url";
import "./styles.css";

// Set the window/taskbar favicon. In --app mode (puppeteer launcher) this
// drives the title-bar and taskbar icon.
const existingIcon = document.querySelector<HTMLLinkElement>("link[rel='icon']");
if (existingIcon) {
  existingIcon.href = iconUrl;
} else {
  const link = document.createElement("link");
  link.rel = "icon";
  link.type = "image/png";
  link.href = iconUrl;
  document.head.appendChild(link);
}

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("root element missing");
createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>
);
