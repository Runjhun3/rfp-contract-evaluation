import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Criteria from "./pages/Criteria";
import Evidence from "./pages/Evidence";
import NewProject from "./pages/NewProject";
import NotFound from "./pages/NotFound";
import OpenProject from "./pages/OpenProject";
import Participants from "./pages/Participants";
import Projects from "./pages/Projects";
import Results from "./pages/Results";
import RfpUpload from "./pages/RfpUpload";
import RunProgress from "./pages/RunProgress";

// One route per screen of the UI design. The same paths are the stepper's links.
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/projects" replace />} />
        <Route path="projects" element={<Projects />} />
        <Route path="projects/new" element={<NewProject />} />
        <Route path="projects/:tenderId" element={<OpenProject />} />
        <Route path="projects/:tenderId/rfp" element={<RfpUpload />} />
        <Route path="projects/:tenderId/criteria" element={<Criteria />} />
        <Route path="projects/:tenderId/participants" element={<Participants />} />
        <Route path="runs/:runId" element={<RunProgress />} />
        <Route path="runs/:runId/results" element={<Results />} />
        <Route path="scores/:scoreId" element={<Evidence />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
