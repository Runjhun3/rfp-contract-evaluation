import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { post } from "../api";
import { usePageTitle } from "../components/Layout";
import ProjectHead from "../components/ProjectHead";
import { ErrorText, Loading } from "../components/Status";
import type { RfpPage } from "../types";
import { useApi } from "../useApi";

export default function RfpUpload() {
  const { tenderId } = useParams();
  const navigate = useNavigate();
  const { data, error } = useApi<RfpPage>(`/api/v1/projects/${tenderId}/rfp`);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  usePageTitle(data && `RFP · ${data.project.name}`);
  if (!data) return <Loading error={error} />;

  async function upload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    try {
      await post(`/api/v1/projects/${tenderId}/rfp`, new FormData(e.currentTarget));
      navigate(`/projects/${tenderId}/criteria`);
    } catch (err) {
      setUploadError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <ProjectHead project={data.project} steps={data.steps} />
      <ErrorText error={uploadError} />
      <section className="card">
        <h2>RFP document</h2>
        {data.rfp && (
          <div className="row">
            <strong>{data.rfp.file_name}</strong>
            <span className="muted">{data.rfp.page_count} pages · uploaded {data.rfp.uploaded}</span>
          </div>
        )}
        <form className="drop" onSubmit={upload}>
          <label className="field">{data.rfp ? "Replace the RFP PDF" : "Upload the RFP PDF"}
            <input type="file" name="file" accept="application/pdf" required />
          </label>
          <div className="row">
            <button className="btn primary" type="submit" disabled={busy}>
              {busy ? "Uploading…" : "Upload and find criteria"}
            </button>
            <span className="small muted">PDF up to 150 MB</span>
          </div>
        </form>
        <p className="small muted">
          After upload the evaluation criteria are read from the RFP, wherever they appear, and
          shown to you to check.
        </p>
      </section>
    </main>
  );
}
