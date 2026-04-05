import { Navigate, useParams } from "react-router-dom";

export default function MissionContent() {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/missions/${id}`} replace />;
}
