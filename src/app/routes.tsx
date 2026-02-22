import { createBrowserRouter } from "react-router";
import { Layout } from "./Layout";
import { Home } from "./views/Home";
import { Login } from "./views/Login";
import { DashboardPage } from "./views/DashboardPage";
import { Vault } from "./views/Vault";
import { ClinicianPortal } from "./views/ClinicianPortal";
import { BodyModel } from "./components/results/BodyModel";
import { Present } from "./views/Present";

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
        path: "login",
        Component: Login,
      },
      {
        path: "dashboard",
        Component: DashboardPage,
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
      {
        path: "body",
        Component: () => <BodyModel onClose={() => window.history.back()} />,
      },
      {
        path: "present",
        Component: Present,
      },
    ],
  },
]);
