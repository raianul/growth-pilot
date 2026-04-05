import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";

interface CheckoutResponse {
  checkout_url: string;
}

interface PortalResponse {
  portal_url: string;
}

interface OrgResponse {
  id: string;
  business_name: string;
  tier?: string;
}

const PLANS = [
  {
    tier: "pro",
    name: "Pro",
    price: "$49",
    period: "/ month",
    description: "For growing local businesses",
    features: [
      "Weekly automated audits",
      "Up to 10 missions / month",
      "AI-powered content drafts",
      "Competitor tracking (5)",
      "Email + Telegram alerts",
    ],
    gradient: "from-primary to-primary-container",
  },
  {
    tier: "agency",
    name: "Agency",
    price: "$149",
    period: "/ month",
    description: "For agencies managing multiple clients",
    features: [
      "Everything in Pro",
      "Unlimited brands",
      "Daily audits",
      "Priority AI processing",
      "White-label reports",
      "Dedicated support",
    ],
    gradient: "from-violet-600 to-indigo-700",
  },
];

export default function Billing() {
  const [checkoutError, setCheckoutError] = useState<string | null>(null);

  const { data: org } = useQuery({
    queryKey: ["organization"],
    queryFn: () => apiFetch<OrgResponse>("/organizations/me"),
  });

  // Default to "free" if tier not returned by backend yet
  const currentPlan = org?.tier ?? "free";

  const { mutate: startCheckout, isPending: checkoutPending } = useMutation({
    mutationFn: (tier: string) =>
      apiFetch<CheckoutResponse>("/billing/checkout", {
        method: "POST",
        body: JSON.stringify({ tier }),
      }),
    onSuccess: (data) => {
      window.location.href = data.checkout_url;
    },
    onError: (err: Error) => setCheckoutError(err.message),
  });

  const { mutate: openPortal, isPending: portalPending } = useMutation({
    mutationFn: () => apiFetch<PortalResponse>("/billing/portal", { method: "POST" }),
    onSuccess: (data) => {
      window.location.href = data.portal_url;
    },
  });

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="font-headline font-extrabold text-on-surface text-3xl">
          Billing
        </h1>
        <p className="text-on-surface-variant mt-1">
          Upgrade your plan to unlock more audits, missions, and AI power.
        </p>
        {/* Current plan banner */}
        <div className="inline-flex items-center gap-2 mt-3 px-3 py-1.5 rounded-lg bg-primary/8 text-primary text-sm font-semibold">
          <span
            className="material-symbols-outlined text-base"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            verified
          </span>
          You're on the{" "}
          <span className="capitalize">{currentPlan === "free" ? "Free" : currentPlan}</span>{" "}
          plan
        </div>
      </div>

      {/* Plans */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {PLANS.map((plan) => (
          <div
            key={plan.tier}
            className="bg-surface-container-lowest rounded-xl p-6 shadow-ambient flex flex-col"
          >
            <div
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gradient-to-r ${plan.gradient} text-white text-sm font-semibold mb-4 self-start`}
            >
              {plan.name}
            </div>

            <div className="mb-4">
              <span className="font-headline font-extrabold text-on-surface text-4xl">
                {plan.price}
              </span>
              <span className="text-on-surface-variant text-sm ml-1">
                {plan.period}
              </span>
            </div>

            <p className="text-on-surface-variant text-sm mb-5">
              {plan.description}
            </p>

            <ul className="space-y-2.5 mb-6 flex-1">
              {plan.features.map((f) => (
                <li
                  key={f}
                  className="flex items-center gap-2.5 text-sm text-on-surface"
                >
                  <span
                    className="material-symbols-outlined text-primary text-base flex-shrink-0"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    check_circle
                  </span>
                  {f}
                </li>
              ))}
            </ul>

            {currentPlan === plan.tier ? (
              <div className="w-full py-3 rounded-xl flex items-center justify-center gap-2 bg-primary/8 text-primary text-sm font-semibold">
                <span
                  className="material-symbols-outlined text-base"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  check_circle
                </span>
                Current Plan
              </div>
            ) : (
              <button
                onClick={() => startCheckout(plan.tier)}
                disabled={checkoutPending}
                className={`w-full py-3 rounded-xl text-white font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 bg-gradient-to-r ${plan.gradient}`}
              >
                {checkoutPending ? "Loading…" : `Upgrade to ${plan.name}`}
              </button>
            )}
          </div>
        ))}
      </div>

      {checkoutError && (
        <p className="text-red-500 text-sm">{checkoutError}</p>
      )}

      {/* Manage subscription */}
      <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient flex items-center justify-between gap-4">
        <div>
          <h3 className="font-headline font-extrabold text-on-surface text-base">
            Manage subscription
          </h3>
          <p className="text-on-surface-variant text-sm mt-0.5">
            Update payment method, cancel, or view invoices.
          </p>
        </div>
        <button
          onClick={() => openPortal()}
          disabled={portalPending}
          className="flex-shrink-0 px-4 py-2.5 rounded-xl bg-surface-container-low text-on-surface text-sm font-semibold hover:bg-surface-container-high transition-colors disabled:opacity-50"
        >
          {portalPending ? "Loading…" : "Customer portal →"}
        </button>
      </div>
    </div>
  );
}
