import { useState } from "react";
import SearchPage from "./pages/SearchPage";
import ResultsPage from "./pages/ResultsPage";
import RestaurantPage from "./pages/RestaurantPage";

type Route =
  | { page: "search" }
  | { page: "results"; query: string; postcode?: string }
  | { page: "restaurant"; slug: string };

export default function App() {
  const [route, setRoute] = useState<Route>({ page: "search" });

  if (route.page === "results") {
    return (
      <ResultsPage
        query={route.query}
        postcode={route.postcode}
        onSelectRestaurant={(slug) => setRoute({ page: "restaurant", slug })}
        onBack={() => setRoute({ page: "search" })}
        onNewSearch={(q, p) => setRoute({ page: "results", query: q, postcode: p })}
      />
    );
  }

  if (route.page === "restaurant") {
    return <RestaurantPage slug={route.slug} onBack={() => window.history.back()} />;
  }

  return <SearchPage onSearch={(q, p) => setRoute({ page: "results", query: q, postcode: p })} />;
}
