import { Navigate, useParams } from "react-router-dom";
import { Loading } from "../components/Status";
import { useApi } from "../useApi";

// Opening a project lands on the step it has reached (the API decides which).
export default function OpenProject() {
  const { tenderId } = useParams();
  const { data, error } = useApi<{ landing: string }>(`/api/v1/projects/${tenderId}`);
  if (!data) return <Loading error={error} />;
  return <Navigate to={data.landing} replace />;
}
