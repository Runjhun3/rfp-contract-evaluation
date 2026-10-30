import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/app.css";
import "./styles/eligibility.css";
import "./styles/section.css";

// A data router around the app's own <Routes>: it lets a form with unsaved changes ask
// before the user leaves (useUnsaved.ts). The routes themselves stay in App.tsx.
const router = createBrowserRouter([{ path: "*", element: <App /> }]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
