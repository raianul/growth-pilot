import { useEffect, useState } from "react";
import AuditPage from "./AuditPage";
import BusinessSearch from "./BusinessSearch";
import type { StartAuditPayload } from "./BusinessSearch";

function Icon({ name, className = "" }: { name: string; className?: string }) {
  return (
    <span className={`material-symbols-outlined ${className}`}>{name}</span>
  );
}

/* ------------------------------------------------------------------ */
/*  Hero                                                               */
/* ------------------------------------------------------------------ */

function Hero({ onStartAudit }: { onStartAudit: (payload: StartAuditPayload) => void }) {
  return (
    <section className="bg-gradient-to-br from-primary to-primary-container px-6 pt-16 pb-20 md:pt-24 md:pb-28">
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="font-headline text-3xl font-extrabold leading-tight tracking-tight text-white md:text-5xl">
          See how your restaurant looks online — for free
        </h1>
        <p className="mt-4 text-base text-white/80 md:text-lg">
          Compare your Google Maps, Facebook &amp; Instagram with competitors in
          your area. Takes 60 seconds.
        </p>

        <div className="mt-8">
          <BusinessSearch onStartAudit={onStartAudit} variant="hero" />
        </div>

        <p className="mt-4 text-xs text-white/50">
          No signup required. Your data stays private.
        </p>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  How It Works                                                       */
/* ------------------------------------------------------------------ */

const steps = [
  {
    icon: "search",
    title: "Find your restaurant",
    desc: "Search by name or paste your Google Maps link. That's all we need.",
  },
  {
    icon: "compare_arrows",
    title: "See how you compare",
    desc: "We check your listing against nearby restaurants — reviews, rating, and more.",
  },
  {
    icon: "task_alt",
    title: "Get told what to fix",
    desc: "We show your biggest gaps and give you copy-paste content to close them.",
  },
];

function HowItWorks() {
  return (
    <section className="px-6 py-16 md:py-24">
      <div className="mx-auto max-w-4xl">
        <h2 className="text-center font-headline text-2xl font-extrabold text-on-surface md:text-3xl">
          How it works
        </h2>

        <div className="mt-12 grid gap-8 md:grid-cols-3">
          {steps.map((step, i) => (
            <div key={i} className="text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
                <Icon name={step.icon} className="text-primary text-2xl" />
              </div>
              <div className="mt-3 text-xs font-bold text-primary/60 uppercase tracking-widest">
                Step {i + 1}
              </div>
              <h3 className="mt-2 font-headline text-lg font-extrabold text-on-surface">
                {step.title}
              </h3>
              <p className="mt-2 text-sm text-on-surface-variant leading-relaxed">
                {step.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Preview                                                            */
/* ------------------------------------------------------------------ */

function Preview() {
  return (
    <section className="bg-surface-container-low px-6 py-16 md:py-24">
      <div className="mx-auto max-w-3xl">
        <h2 className="text-center font-headline text-2xl font-extrabold text-on-surface md:text-3xl">
          What you'll see
        </h2>
        <p className="mt-3 text-center text-on-surface-variant">
          A complete picture of your online presence in 60 seconds.
        </p>

        <div className="mt-10 space-y-4">
          <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100">
                <Icon name="location_on" className="text-green-600" />
              </div>
              <div>
                <div className="font-headline font-extrabold text-on-surface">Google Maps</div>
                <div className="text-sm text-on-surface-variant">4.5★ · 990 reviews</div>
              </div>
              <span className="ml-auto rounded-full bg-green-100 px-3 py-1 text-xs font-bold text-green-700">
                Good
              </span>
            </div>
          </div>

          <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
            <div className="font-headline font-extrabold text-on-surface mb-4">
              How you compare nearby
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <Icon name="store" className="text-primary text-base" />
                </div>
                <div className="flex-1 text-sm text-on-surface">You</div>
                <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-700">Behind area avg</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-container-low">
                  <Icon name="group" className="text-on-surface-variant text-base" />
                </div>
                <div className="flex-1 text-sm text-on-surface">Area average</div>
                <span className="rounded-full bg-surface-container-high px-3 py-1 text-xs font-bold text-on-surface-variant">Benchmark</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-green-100">
                  <Icon name="emoji_events" className="text-green-600 text-base" />
                </div>
                <div className="flex-1 text-sm text-on-surface">Top rival</div>
                <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-bold text-green-700">Leading</span>
              </div>
            </div>
          </div>

          <div className="rounded-lg bg-surface-container-lowest p-5 shadow-ambient">
            <div className="font-headline font-extrabold text-on-surface mb-3">
              What Your Customers Say
            </div>
            <div className="space-y-2">
              <div className="flex items-start gap-2">
                <Icon name="thumb_up" className="text-green-600 text-lg mt-0.5" />
                <span className="text-sm text-on-surface">"Authentic food and great service" — 3 mentions</span>
              </div>
              <div className="flex items-start gap-2">
                <Icon name="thumb_down" className="text-red-500 text-lg mt-0.5" />
                <span className="text-sm text-on-surface">"Long wait times during peak hours" — 2 mentions</span>
              </div>
              <div className="flex items-start gap-2">
                <Icon name="lightbulb" className="text-amber-500 text-lg mt-0.5" />
                <span className="text-sm text-on-surface">"Set up a reservation system to reduce wait times"</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Footer                                                             */
/* ------------------------------------------------------------------ */

function Footer() {
  return (
    <footer className="bg-surface-container-high px-6 py-10">
      <div className="mx-auto max-w-4xl text-center">
        <div className="font-headline font-extrabold text-on-surface">
          GrowthPilot
        </div>
        <p className="mt-2 text-sm text-on-surface-variant">
          We make restaurants easier to find online.
        </p>
        <div className="mt-4 flex justify-center gap-6 text-sm text-on-surface-variant">
          <a href="/privacy" className="min-h-[44px] inline-flex items-center hover:text-on-surface transition">Privacy Policy</a>
          <a href="/terms" className="min-h-[44px] inline-flex items-center hover:text-on-surface transition">Terms of Service</a>
        </div>
        <p className="mt-6 text-xs text-on-surface-variant/60">
          © 2026 GrowthPilot. All rights reserved.
        </p>
      </div>
    </footer>
  );
}

/* ------------------------------------------------------------------ */
/*  Landing Page                                                       */
/* ------------------------------------------------------------------ */

function LandingPage({ onStartAudit }: { onStartAudit: (payload: StartAuditPayload) => void }) {
  return (
    <div id="top">
      <Hero onStartAudit={onStartAudit} />
      <HowItWorks />
      <Preview />
      <Footer />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  App Router                                                         */
/* ------------------------------------------------------------------ */

function parseRoute(): { page: "landing" } | { page: "audit"; slug: string; renew: boolean } {
  const path = window.location.pathname;
  const params = new URLSearchParams(window.location.search);

  // /audit/{slug}
  const auditMatch = path.match(/^\/audit\/(.+)$/);
  if (auditMatch) {
    return { page: "audit", slug: auditMatch[1], renew: params.get("renew") === "true" };
  }

  // Everything else → landing
  return { page: "landing" };
}

export default function App() {
  const [route, setRoute] = useState(parseRoute);

  // Listen for popstate (back/forward)
  useEffect(() => {
    function onPop() { setRoute(parseRoute()); }
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  function navigateTo(path: string) {
    window.history.pushState(null, "", path);
    setRoute(parseRoute());
    window.scrollTo(0, 0);
  }

  function handleStartAudit(payload: StartAuditPayload) {
    if (payload.slug) {
      navigateTo(`/audit/${payload.slug}`);
    } else {
      navigateTo(`/audit/_pid_${payload.google_place_id}`);
    }
  }

  function goHome() {
    window.history.pushState(null, "", "/");
    setRoute({ page: "landing" });
    window.scrollTo(0, 0);
  }

  if (route.page === "audit") {
    return (
      <AuditPage
        audit={{ type: "slug", slug: route.slug, renew: route.renew }}
        onBack={goHome}
      />
    );
  }


  return <LandingPage onStartAudit={handleStartAudit} />;
}
