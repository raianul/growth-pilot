import { useState, type FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";

interface Outlet {
  id: string;
  outlet_name: string;
  city: string;
  address: string | null;
  google_place_id: string | null;
  next_audit_at: string | null;
}

interface EditState {
  outletId: string;
  outlet_name: string;
  city: string;
  address: string;
}

export default function Outlets() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [editState, setEditState] = useState<EditState | null>(null);

  // New outlet form state
  const [newName, setNewName] = useState("");
  const [newCity, setNewCity] = useState("");
  const [newAddress, setNewAddress] = useState("");
  const [addError, setAddError] = useState<string | null>(null);

  const { data: outlets, isLoading } = useQuery({
    queryKey: ["outlets"],
    queryFn: () => apiFetch<Outlet[]>("/outlets"),
  });

  const { mutate: addOutlet, isPending: adding } = useMutation({
    mutationFn: () =>
      apiFetch("/outlets", {
        method: "POST",
        body: JSON.stringify({
          outlet_name: newName.trim(),
          city: newCity.trim(),
          address: newAddress.trim() || undefined,
        }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["outlets"] });
      setShowAdd(false);
      setNewName("");
      setNewCity("");
      setNewAddress("");
      setAddError(null);
    },
    onError: (err: Error) => {
      setAddError(err.message);
    },
  });

  const { mutate: updateOutlet, isPending: updating } = useMutation({
    mutationFn: (data: EditState) =>
      apiFetch(`/outlets/${data.outletId}`, {
        method: "PATCH",
        body: JSON.stringify({
          outlet_name: data.outlet_name.trim(),
          city: data.city.trim(),
          address: data.address.trim() || undefined,
        }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["outlets"] });
      setEditState(null);
    },
  });

  function handleAddSubmit(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim() || !newCity.trim()) return;
    addOutlet();
  }

  function handleEditSubmit(e: FormEvent) {
    e.preventDefault();
    if (!editState || !editState.outlet_name.trim() || !editState.city.trim())
      return;
    updateOutlet(editState);
  }

  function startEdit(outlet: Outlet) {
    setEditState({
      outletId: outlet.id,
      outlet_name: outlet.outlet_name,
      city: outlet.city,
      address: outlet.address ?? "",
    });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-headline font-extrabold text-on-surface text-3xl">
            Outlets
          </h1>
          <p className="text-on-surface-variant mt-1">
            Manage your business locations.
          </p>
        </div>
        <button
          onClick={() => {
            setShowAdd((v) => !v);
            setEditState(null);
          }}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          <span className="material-symbols-outlined text-base">add</span>
          Add outlet
        </button>
      </div>

      {/* Add outlet form */}
      {showAdd && (
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-ambient">
          <h2 className="font-headline font-extrabold text-on-surface text-lg mb-4">
            New outlet
          </h2>
          <form onSubmit={handleAddSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-on-surface mb-1.5">
                Location name
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
                placeholder="e.g. Joe's Pizza — Midtown"
                className="w-full px-4 py-3 rounded-xl bg-surface-container-low text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-on-surface mb-1.5">
                City
              </label>
              <input
                type="text"
                value={newCity}
                onChange={(e) => setNewCity(e.target.value)}
                required
                placeholder="e.g. New York"
                className="w-full px-4 py-3 rounded-xl bg-surface-container-low text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-on-surface mb-1.5">
                Address{" "}
                <span className="text-on-surface-variant font-normal">
                  (optional)
                </span>
              </label>
              <input
                type="text"
                value={newAddress}
                onChange={(e) => setNewAddress(e.target.value)}
                placeholder="e.g. 123 Main St"
                className="w-full px-4 py-3 rounded-xl bg-surface-container-low text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>
            {addError && <p className="text-red-500 text-sm">{addError}</p>}
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={adding || !newName.trim() || !newCity.trim()}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {adding ? "Adding…" : "Add outlet"}
              </button>
              <button
                type="button"
                onClick={() => setShowAdd(false)}
                className="px-5 py-2.5 rounded-xl bg-surface-container-low text-on-surface-variant text-sm font-semibold hover:text-on-surface transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Outlet list */}
      {!outlets || outlets.length === 0 ? (
        <div className="text-center py-12 bg-surface-container-lowest rounded-xl shadow-ambient">
          <span className="material-symbols-outlined text-5xl text-on-surface-variant mb-3 block">
            store
          </span>
          <p className="text-on-surface-variant">
            No outlets yet. Add your first location to get started.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {outlets.map((outlet) => (
            <div key={outlet.id}>
              {editState?.outletId === outlet.id ? (
                <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient">
                  <h3 className="font-headline font-extrabold text-on-surface text-base mb-4">
                    Edit outlet
                  </h3>
                  <form onSubmit={handleEditSubmit} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-on-surface mb-1.5">
                        Location name
                      </label>
                      <input
                        type="text"
                        value={editState.outlet_name}
                        onChange={(e) =>
                          setEditState({ ...editState, outlet_name: e.target.value })
                        }
                        required
                        className="w-full px-4 py-3 rounded-xl bg-surface-container-low text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/30"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-on-surface mb-1.5">
                        City
                      </label>
                      <input
                        type="text"
                        value={editState.city}
                        onChange={(e) =>
                          setEditState({ ...editState, city: e.target.value })
                        }
                        required
                        className="w-full px-4 py-3 rounded-xl bg-surface-container-low text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/30"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-on-surface mb-1.5">
                        Address{" "}
                        <span className="text-on-surface-variant font-normal">
                          (optional)
                        </span>
                      </label>
                      <input
                        type="text"
                        value={editState.address}
                        onChange={(e) =>
                          setEditState({ ...editState, address: e.target.value })
                        }
                        className="w-full px-4 py-3 rounded-xl bg-surface-container-low text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/30"
                      />
                    </div>
                    <div className="flex gap-3">
                      <button
                        type="submit"
                        disabled={
                          updating ||
                          !editState.outlet_name.trim() ||
                          !editState.city.trim()
                        }
                        className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-container text-white text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
                      >
                        {updating ? "Saving…" : "Save"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditState(null)}
                        className="px-5 py-2.5 rounded-xl bg-surface-container-low text-on-surface-variant text-sm font-semibold hover:text-on-surface transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                </div>
              ) : (
                <div className="bg-surface-container-lowest rounded-xl p-5 shadow-ambient flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <span
                      className="material-symbols-outlined text-primary text-xl"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      store
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-headline font-extrabold text-on-surface text-base truncate">
                      {outlet.outlet_name}
                    </h3>
                    <p className="text-sm text-on-surface-variant">
                      {outlet.city}
                      {outlet.address ? ` · ${outlet.address}` : ""}
                    </p>
                    {outlet.next_audit_at && (
                      <p className="text-xs text-on-surface-variant mt-0.5">
                        Next audit:{" "}
                        {new Date(outlet.next_audit_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => startEdit(outlet)}
                    className="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors"
                    aria-label="Edit outlet"
                  >
                    <span className="material-symbols-outlined text-xl">
                      edit
                    </span>
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
