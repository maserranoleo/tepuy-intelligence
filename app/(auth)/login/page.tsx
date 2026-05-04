import LoginForm from "@/components/LoginForm";

export default function LoginPage() {
  return (
    <main className="login-shell">
      <div className="login-glow" aria-hidden />
      <div className="login-topo" aria-hidden />
      <div className="login-ridge" aria-hidden />

      <div className="login-card">
        <div className="tagline">
          <span className="tagline-glyph">◭</span>
          <span>Latin America Energy Intelligence</span>
        </div>

        <h1 className="brand">Tepuy Intelligence</h1>

        <div className="subtitle-row">
          <span className="subtitle-rule" />
          <span className="subtitle">Elevated Vantage</span>
          <span className="subtitle-rule" />
        </div>

        <LoginForm />

        <div className="preview-note">
          <span>◌</span>
          <span>Preview</span>
        </div>
      </div>
    </main>
  );
}
