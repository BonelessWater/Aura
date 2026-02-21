import { createBrowserRouter } from "react-router";
import { Layout } from "./Layout";
import { Home } from "./views/Home";
import { Vault } from "./views/Vault";
import { ClinicianPortal } from "./views/ClinicianPortal";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      {
        index: true,
        Component: Home,
      },
      {
        path: "vault",
        Component: Vault,
      },
      {
        path: "clinician/:id",
        Component: ClinicianPortal,
      },
      {
        path: "clinician",
        Component: ClinicianPortal,
      },
    ],
  },
]);
