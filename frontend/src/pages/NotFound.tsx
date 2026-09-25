import { Link } from "react-router-dom";
import { usePageTitle } from "../components/Layout";

export default function NotFound() {
  usePageTitle("Not found");
  return (
    <main className="page">
      <h1>Not found</h1>
      <p>This page does not exist.</p>
      <p><Link to="/projects">Back to projects</Link></p>
    </main>
  );
}
