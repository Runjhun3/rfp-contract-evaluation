import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth";
import Criteria from "./pages/Criteria";
import Eligibility from "./pages/Eligibility";
import EligibilityCheck from "./pages/EligibilityCheck";
import Evidence from "./pages/Evidence";
import Login from "./pages/Login";
import NewProject from "./pages/NewProject";
import NotFound from "./pages/NotFound";
import OpenProject from "./pages/OpenProject";
import Participants from "./pages/Participants";
import Projects from "./pages/Projects";
import Results from "./pages/Results";
import RfpUpload from "./pages/RfpUpload";
import RunProgress from "./pages/RunProgress";

// One route per screen of the UI design. The same paths are the stepper's links.
// Everything except /login needs a signed-in session (RequireAuth).
export default function App() {
  return (
    <Routes>
      <Route path="login" element={<Login />} />
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/projects" replace />} />
          <Route path="projects" element={<Projects />} />
          <Route path="projects/new" element={<NewProject />} />
          <Route path="projects/:tenderId" element={<OpenProject />} />
          <Route path="projects/:tenderId/rfp" element={<RfpUpload />} />
          <Route path="projects/:tenderId/criteria" element={<Criteria />} />
          <Route path="projects/:tenderId/participants" element={<Participants />} />
          <Route path="projects/:tenderId/eligibility" element={<Eligibility />} />
          <Route path="eligibility/:checkId" element={<EligibilityCheck />} />
          <Route path="runs/:runId" element={<RunProgress />} />
          <Route path="projects/:tenderId/results" element={<Results />} />
          <Route path="scores/:scoreId" element={<Evidence />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  );
}
