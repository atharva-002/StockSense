import { Database, GitBranch, Package, Server, Activity, GitCommit, Boxes, Workflow } from "lucide-react";

const STEPS = [
  { icon: Database, title: "Raw data", desc: "Public retail daily sales CSV, versioned in data/raw/" },
  { icon: Workflow, title: "Feature engineering", desc: "Lags 7/14/28/364, rolling means + std, calendar, holidays" },
  { icon: Boxes, title: "Training", desc: "Seasonal naive + Ridge + LightGBM quantile (0.1 / 0.5 / 0.9)" },
  { icon: GitCommit, title: "MLflow + quality gate", desc: "Params/metrics/artifacts; CI fails if MAPE ≥ threshold or ≥ naive" },
  { icon: Package, title: "Dockerized API", desc: "Slim Python 3.11-slim image, non-root user, healthcheck" },
  { icon: GitBranch, title: "GitHub Actions", desc: "Lint + tests + training smoke + docker build on every PR" },
  { icon: Server, title: "Deploy", desc: "Render (free) via render.yaml · AWS ECS Fargate via Terraform" },
  { icon: Activity, title: "Monitoring + retrain", desc: "Weekly PSI/KS drift check → auto-retrain if drift detected" },
];

const STACK = [
  { label: "Modelling", items: ["LightGBM", "Scikit-learn (Ridge)", "SHAP (offline)"] },
  { label: "Serving", items: ["FastAPI", "Uvicorn", "Pandas / NumPy"] },
  { label: "MLOps", items: ["MLflow", "Pytest", "Ruff", "Docker + Compose"] },
  { label: "CI / CD", items: ["GitHub Actions", "Render deploy hook", "Weekly retrain workflow"] },
  { label: "Infra", items: ["Terraform (S3, ECR, ECS Fargate, IAM, CloudWatch)"] },
  { label: "Frontend", items: ["React 19", "Tailwind + shadcn/ui", "Recharts"] },
];

export default function ArchitecturePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-heading tracking-tight font-bold text-gray-900">
          MLOps Architecture
        </h1>
        <p className="text-sm text-gray-600 mt-2 max-w-2xl">
          Every step from a raw CSV to a deployed, monitored and automatically retrained forecasting
          service.
        </p>
      </div>

      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-heading font-semibold text-gray-900 mb-6">Pipeline</h2>
        <ol className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5" data-testid="pipeline-steps">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            return (
              <li
                key={s.title}
                className="relative bg-gray-50 border border-gray-200 rounded-xl p-5 flex flex-col gap-3"
                data-testid={`pipeline-step-${i}`}
              >
                <span className="absolute -top-2 -left-2 w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs font-semibold">
                  {i + 1}
                </span>
                <span className="w-9 h-9 rounded-lg bg-white border border-gray-200 flex items-center justify-center">
                  <Icon className="w-4 h-4 text-indigo-600" />
                </span>
                <h3 className="text-sm font-medium text-gray-900">{s.title}</h3>
                <p className="text-xs text-gray-600 leading-relaxed">{s.desc}</p>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-heading font-semibold text-gray-900 mb-6">Tech stack</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {STACK.map((cat) => (
            <div key={cat.label} className="border border-gray-200 rounded-xl p-5 bg-gray-50">
              <div className="text-[10px] tracking-wider uppercase font-semibold text-gray-500 mb-3">
                {cat.label}
              </div>
              <div className="flex flex-wrap gap-2">
                {cat.items.map((i) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border border-indigo-200 text-indigo-700 bg-white"
                  >
                    {i}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
