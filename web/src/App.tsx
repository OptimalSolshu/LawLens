import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Empty } from "./components/ui";
import { DraftsPage } from "./pages/DraftsPage";
import { ImpactPage } from "./pages/ImpactPage";
import { LawsPage } from "./pages/LawsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/laws" replace />} />
        <Route path="laws" element={<LawsPage />} />
        <Route path="laws/:lawId" element={<LawsPage />} />
        <Route path="laws/:lawId/:number" element={<LawsPage />} />
        <Route path="impact" element={<ImpactPage />} />
        <Route path="drafts" element={<DraftsPage />} />
        <Route path="drafts/:draftId" element={<DraftsPage />} />
        <Route path="*" element={<Empty text="Хуудас олдсонгүй." />} />
      </Route>
    </Routes>
  );
}
