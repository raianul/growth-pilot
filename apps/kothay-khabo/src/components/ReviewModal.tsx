import { useState } from "react";
import { phoneAuth, submitReview } from "../lib/api";
import { getStoredUser, storeUser } from "../lib/auth";

function Icon({ name, className = "", fill = false }: { name: string; className?: string; fill?: boolean }) {
  return (
    <span
      className={`material-symbols-outlined ${className}`}
      style={fill ? ({ fontVariationSettings: "'FILL' 1" } as React.CSSProperties) : undefined}
    >
      {name}
    </span>
  );
}

type Step = "auth" | "q1" | "q2" | "q3" | "done";

interface ReviewModalProps {
  businessId: string;
  onClose: () => void;
}

export default function ReviewModal({ businessId, onClose }: ReviewModalProps) {
  const [step, setStep] = useState<Step>(() => (getStoredUser() ? "q1" : "auth"));
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [food, setFood] = useState<boolean | null>(null);
  const [env, setEnv] = useState<boolean | null>(null);
  const [submitError, setSubmitError] = useState("");

  async function handleAuth() {
    if (!phone.match(/^01[3-9]\d{8}$/)) {
      setAuthError("Valid Bangladeshi number required (e.g. 01XXXXXXXXX)");
      return;
    }
    setAuthLoading(true);
    setAuthError("");
    try {
      const user = await phoneAuth(phone, name.trim() || undefined);
      storeUser(user);
      setStep("q1");
    } catch {
      setAuthError("Could not verify number. Please try again.");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleAnswer(question: "q1" | "q2" | "q3", answer: boolean) {
    if (question === "q1") {
      setFood(answer);
      setStep("q2");
    } else if (question === "q2") {
      setEnv(answer);
      setStep("q3");
    } else {
      // q3 — auto-submit
      const user = getStoredUser();
      if (!user) { setStep("auth"); return; }
      try {
        await submitReview(user.user_id, businessId, food!, env!, answer);
        setSubmitError("");
      } catch (err: unknown) {
        setSubmitError(err instanceof Error ? err.message : "Something went wrong");
      }
      setStep("done");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-on-surface/30"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-surface-container-lowest rounded-t-2xl shadow-ambient p-6 pb-10 animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Handle bar */}
        <div className="w-10 h-1 bg-outline-variant rounded-full mx-auto mb-6" />

        {step === "auth" && (
          <div className="space-y-4">
            <h2 className="font-headline font-extrabold text-xl text-on-surface text-center">
              Quick verification
            </h2>
            <p className="text-sm text-on-surface-variant text-center">
              We need your number to prevent duplicate reviews
            </p>

            <div className="space-y-3">
              <input
                type="tel"
                inputMode="tel"
                placeholder="01XXXXXXXXX"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full bg-surface-container-low rounded-lg px-4 py-3 text-on-surface font-body text-base focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
              <input
                type="text"
                placeholder="Your name (optional)"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-surface-container-low rounded-lg px-4 py-3 text-on-surface font-body text-base focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>

            {authError && (
              <p className="text-red-600 text-sm text-center">{authError}</p>
            )}

            <button
              onClick={handleAuth}
              disabled={authLoading}
              className="w-full py-4 rounded-lg font-headline font-extrabold text-white text-base"
              style={{ background: "linear-gradient(135deg, #0037b0, #1d4ed8)" }}
            >
              {authLoading ? "Verifying..." : "Continue"}
            </button>
          </div>
        )}

        {(step === "q1" || step === "q2" || step === "q3") && (
          <QuestionStep step={step} onAnswer={handleAnswer} />
        )}

        {step === "done" && (
          <div className="flex flex-col items-center gap-4 py-4">
            {submitError ? (
              <>
                <Icon name="info" className="text-5xl text-on-surface-variant" fill />
                <p className="font-body text-on-surface-variant text-center">{submitError}</p>
              </>
            ) : (
              <>
                <Icon name="check_circle" className="text-5xl text-green-500" fill />
                <p className="font-headline font-extrabold text-xl text-on-surface text-center">
                  Thanks!
                </p>
                <p className="font-body text-on-surface-variant text-center text-sm">
                  Your review helps others find great food
                </p>
              </>
            )}
            <button
              onClick={onClose}
              className="w-full py-4 rounded-lg font-headline font-extrabold text-white text-base mt-2"
              style={{ background: "linear-gradient(135deg, #0037b0, #1d4ed8)" }}
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

interface QuestionStepProps {
  step: "q1" | "q2" | "q3";
  onAnswer: (question: "q1" | "q2" | "q3", answer: boolean) => void;
}

const QUESTIONS = {
  q1: { emoji: "🍽️", text: "Was the food good?" },
  q2: { emoji: "✨", text: "Was the environment good?" },
  q3: { emoji: "👥", text: "Would you recommend this to friends & family?" },
};

function QuestionStep({ step, onAnswer }: QuestionStepProps) {
  const { emoji, text } = QUESTIONS[step];
  const stepNum = step === "q1" ? 1 : step === "q2" ? 2 : 3;

  return (
    <div className="space-y-6">
      {/* Progress dots */}
      <div className="flex justify-center gap-1.5">
        {[1, 2, 3].map((n) => (
          <div
            key={n}
            className={`h-1.5 rounded-full transition-all ${
              n === stepNum ? "w-6 bg-primary" : n < stepNum ? "w-4 bg-primary/40" : "w-4 bg-outline-variant"
            }`}
          />
        ))}
      </div>

      <div className="text-center space-y-1">
        <span className="text-4xl">{emoji}</span>
        <h2 className="font-headline font-extrabold text-xl text-on-surface mt-2">{text}</h2>
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => onAnswer(step, false)}
          className="flex-1 flex flex-col items-center justify-center gap-2 py-4 bg-red-50 rounded-lg active:scale-95 transition-transform"
        >
          <span className="material-symbols-outlined text-3xl text-red-500">thumb_down</span>
          <span className="font-body text-sm font-semibold text-red-600">No</span>
        </button>
        <button
          onClick={() => onAnswer(step, true)}
          className="flex-1 flex flex-col items-center justify-center gap-2 py-4 bg-green-50 rounded-lg active:scale-95 transition-transform"
        >
          <span className="material-symbols-outlined text-3xl text-green-600">thumb_up</span>
          <span className="font-body text-sm font-semibold text-green-700">Yes</span>
        </button>
      </div>
    </div>
  );
}
