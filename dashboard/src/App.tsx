import { Route, Routes } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { RequireAuth } from "@/components/RequireAuth";
import { AnalyticsPage } from "@/pages/AnalyticsPage";
import { ApprovalsPage } from "@/pages/ApprovalsPage";
import { CampaignsPage } from "@/pages/CampaignsPage";
import { LeadDetailPage } from "@/pages/LeadDetailPage";
import { LeadsPage } from "@/pages/LeadsPage";
import { LoginPage } from "@/pages/LoginPage";
import { OverviewPage } from "@/pages/OverviewPage";
import { SuppressionPage } from "@/pages/SuppressionPage";
import { TargetsPage } from "@/pages/TargetsPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<OverviewPage />} />
        <Route path="campaigns" element={<CampaignsPage />} />
        <Route path="leads" element={<LeadsPage />} />
        <Route path="leads/:id" element={<LeadDetailPage />} />
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="targets" element={<TargetsPage />} />
        <Route path="suppression" element={<SuppressionPage />} />
      </Route>
    </Routes>
  );
}
