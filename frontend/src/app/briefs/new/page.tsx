import '../../brief-new.css';
import AppShell from '@/components/shell/AppShell';
import BriefForm from '@/components/briefs/BriefForm';

export default function NewBriefPage() {
  return (
    <AppShell
      crumbs={[
        { label: 'Workspace', href: '/dashboard' },
        { label: 'Campaign Briefs', href: '/briefs' },
        { label: 'New brief', current: true }
      ]}
      showSearch={false}
    >
      <main className="content">
        <div className="page-head">
          <div>
            <h1>New campaign <span className="accent">brief.</span></h1>
            <p className="sub">Tell us about your campaign — our AI will rank 50,000+ creators against your goals.</p>
          </div>
          <div className="stepper">
            <span className="dot active">1</span><span className="lab">Brief</span>
            <span className="sep"></span>
            <span className="dot">2</span><span>Matches</span>
            <span className="sep"></span>
            <span className="dot">3</span><span>Outreach</span>
          </div>
        </div>

        <BriefForm />
      </main>
    </AppShell>
  );
}
