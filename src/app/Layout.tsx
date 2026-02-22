import { Outlet, useLocation } from "react-router";
import { Background } from "./components/layout/Background";
import { Navbar } from "./components/layout/Navbar";

export const Layout = () => {
  const location = useLocation();
  // Clinician portal has its own light-mode layout—no dark bg or navbar
  const isClinicianPortal = location.pathname.startsWith('/clinician');

  return (
    <>
      {!isClinicianPortal && <Background />}
      <Outlet />
    </>
  );
};
