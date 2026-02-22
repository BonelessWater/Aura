import { Outlet, useLocation } from "react-router";
import { Background } from "./components/layout/Background";
import { Navbar } from "./components/layout/Navbar";

export const Layout = () => {
  const location = useLocation();
  const isClinicianPortal = location.pathname.startsWith('/clinician');

  return (
    <>
      {!isClinicianPortal && <Background />}
      <div className="relative z-10">
        <Outlet />
      </div>
    </>
  );
};
