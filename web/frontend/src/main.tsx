import React from "react";
import ReactDOM from "react-dom/client";
import "antd/dist/reset.css";
import { ConfigProvider, theme } from "antd";
import App from "./App.tsx";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root container not found");
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: "#1677ff",
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>
);
